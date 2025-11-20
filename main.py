"""
M7 Bot - SaaS Cloud Version (V2)
5-Layer Filter System with Supabase Integration
"""

import yfinance as yf
import pandas as pd
import numpy as np
import os
import sys
import json
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import asyncio
from telegram import Bot
from dotenv import load_dotenv

# Import custom modules
from m7_cloud import DBManager
from m7_core import SrVolumeFilter

# Load environment variables
load_dotenv()

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

# ============================================================================
# CONFIGURATION
# ============================================================================
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, 'config.json')

# Load Telegram Config
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

BOT_TOKEN = config['telegram']['bot_token']
CHAT_ID = config['telegram']['chat_id']

# Stock Groups & Thresholds
GROUPS = {
    'A': {'stocks': ['NVDA', 'TSLA'], 'buy_rsi': 25, 'sell_rsi': 65, 'desc': '고변동성'},
    'B': {'stocks': ['META', 'AMZN', 'GOOGL'], 'buy_rsi': 30, 'sell_rsi': 70, 'desc': '중변동성'},
    'C': {'stocks': ['AAPL', 'MSFT'], 'buy_rsi': 35, 'sell_rsi': 75, 'desc': '저변동성'}
}

ALL_STOCKS = []
for g in GROUPS.values():
    ALL_STOCKS.extend(g['stocks'])
ALL_STOCKS.extend(['QQQ', '^TNX'])

# Sentiment Analyzer
analyzer = SentimentIntensityAnalyzer()


# ============================================================================
# OPTIONS ANALYZER (from ultimate_m7_bot.py)
# ============================================================================
class OptionsAnalyzer:
    """옵션 데이터 분석"""
    
    def __init__(self, symbol):
        self.symbol = symbol
        self.ticker = yf.Ticker(symbol)
        
    def get_iv_metrics(self, lookback_days=252):
        """IV Rank 계산"""
        try:
            expirations = self.ticker.options
            if not expirations:
                return None
            
            target_expiry = self._get_target_expiration(expirations)
            opt_chain = self.ticker.option_chain(target_expiry)
            
            current_price = self.ticker.history(period='1d')['Close'].iloc[-1]
            calls = opt_chain.calls
            calls['distance'] = abs(calls['strike'] - current_price)
            atm_call = calls.loc[calls['distance'].idxmin()]
            
            current_iv = atm_call['impliedVolatility']
            hist_ivs = self._get_historical_iv(lookback_days)
            
            if hist_ivs is not None and len(hist_ivs) > 0:
                iv_min = hist_ivs.min()
                iv_max = hist_ivs.max()
                
                if iv_max - iv_min > 0:
                    iv_rank = ((current_iv - iv_min) / (iv_max - iv_min)) * 100
                    iv_rank = max(0, min(100, iv_rank))
                else:
                    iv_rank = 50.0
                
                iv_percentile = (hist_ivs < current_iv).sum() / len(hist_ivs) * 100
            else:
                iv_rank = 50.0
                iv_percentile = 50.0
            
            if iv_rank < 30:
                iv_status = "Low 🟢"
            elif iv_rank < 70:
                iv_status = "Medium 🟡"
            else:
                iv_status = "High 🔴"
            
            return {
                'current_iv': round(current_iv * 100, 2),
                'iv_rank': round(iv_rank, 2),
                'iv_percentile': round(iv_percentile, 2),
                'iv_status': iv_status
            }
            
        except Exception as e:
            print(f"  ⚠️ IV 데이터 수집 실패: {e}")
            return None
    
    def detect_unusual_activity(self):
        """Unusual Options Activity 감지"""
        try:
            expirations = self.ticker.options
            if not expirations:
                return None
            
            near_expiry = expirations[0]
            opt_chain = self.ticker.option_chain(near_expiry)
            
            calls = opt_chain.calls
            puts = opt_chain.puts
            
            call_volume = calls['volume'].sum()
            put_volume = puts['volume'].sum()
            
            pc_ratio = put_volume / call_volume if call_volume > 0 else 999
            
            calls['vol_oi_ratio'] = calls['volume'] / (calls['openInterest'] + 1)
            puts['vol_oi_ratio'] = puts['volume'] / (puts['openInterest'] + 1)
            
            unusual_calls = calls[calls['vol_oi_ratio'] > 2.0]
            unusual_puts = puts[puts['vol_oi_ratio'] > 2.0]
            
            call_volume_threshold = calls['volume'].quantile(0.9)
            put_volume_threshold = puts['volume'].quantile(0.9)
            
            large_calls = calls[calls['volume'] > call_volume_threshold]
            large_puts = puts[puts['volume'] > put_volume_threshold]
            
            bullish_score = 0
            bearish_score = 0
            details = []
            
            if pc_ratio < 0.7:
                bullish_score += 30
                details.append(f"Call 우세 (P/C: {pc_ratio:.2f})")
            elif pc_ratio > 1.3:
                bearish_score += 30
                details.append(f"Put 우세 (P/C: {pc_ratio:.2f})")
            
            if len(unusual_calls) > len(unusual_puts):
                bullish_score += 25
                details.append(f"Call Unusual ({len(unusual_calls)}건)")
            elif len(unusual_puts) > len(unusual_calls):
                bearish_score += 25
                details.append(f"Put Unusual ({len(unusual_puts)}건)")
            
            large_call_value = (large_calls['volume'] * large_calls['lastPrice']).sum()
            large_put_value = (large_puts['volume'] * large_puts['lastPrice']).sum()
            
            if large_call_value > large_put_value * 1.5:
                bullish_score += 25
                details.append(f"대형 Call 매수")
            elif large_put_value > large_call_value * 1.5:
                bearish_score += 25
                details.append(f"대형 Put 매수")
            
            net_score = bullish_score - bearish_score
            
            if net_score > 30:
                signal = "Bullish 🐂"
                confidence = min(bullish_score, 100)
            elif net_score < -30:
                signal = "Bearish 🐻"
                confidence = min(bearish_score, 100)
            else:
                signal = "Neutral ⚖️"
                confidence = 50
            
            return {
                'signal': signal,
                'confidence': confidence,
                'pc_ratio': round(pc_ratio, 2),
                'details': " | ".join(details) if details else "활발한 흐름 없음"
            }
            
        except Exception as e:
            print(f"  ⚠️ Unusual Activity 감지 실패: {e}")
            return None
    
    def _get_target_expiration(self, expirations):
        """30-45일 사이 만기 선택"""
        target_days = 37
        min_diff = 999
        target = expirations[0]
        
        for exp in expirations[:4]:
            exp_date = datetime.strptime(exp, '%Y-%m-%d')
            days = (exp_date - datetime.now()).days
            
            if 20 <= days <= 60:
                diff = abs(days - target_days)
                if diff < min_diff:
                    min_diff = diff
                    target = exp
        
        return target
    
    def _get_historical_iv(self, lookback_days):
        """과거 IV 데이터 수집"""
        try:
            hist = self.ticker.history(period=f"{lookback_days}d")
            hist['log_return'] = np.log(hist['Close'] / hist['Close'].shift(1))
            hist['hv_30'] = hist['log_return'].rolling(window=30).std() * np.sqrt(252)
            return hist['hv_30'].dropna()
        except Exception as e:
            print(f"  ⚠️ 과거 IV 계산 실패: {e}")
            return None
    
    def get_full_options_report(self):
        """전체 옵션 리포트 생성"""
        iv_data = self.get_iv_metrics()
        unusual_data = self.detect_unusual_activity()
        
        return {
            'symbol': self.symbol,
            'iv_metrics': iv_data,
            'unusual_activity': unusual_data,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


# ============================================================================
# TELEGRAM NOTIFICATION
# ============================================================================
async def send_telegram_message(message):
    """텔레그램 메시지 전송"""
    from telegram.request import HTTPXRequest
    
    request = HTTPXRequest(connection_pool_size=8, connect_timeout=20.0, read_timeout=30.0)
    bot = Bot(token=BOT_TOKEN, request=request)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='HTML')
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  재시도 {attempt + 1}/{max_retries - 1}...")
                await asyncio.sleep(2)
            else:
                raise e
    return False


# ============================================================================
# MAIN EXECUTION
# ============================================================================
def main():
    print("="*70)
    print("🚀 M7 Bot - SaaS Cloud Version (V2)")
    print("="*70)
    print()
    
    # Initialize Cloud DB
    try:
        db = DBManager()
        print("✅ Supabase 연결 성공!")
    except Exception as e:
        print(f"❌ Supabase 연결 실패: {e}")
        print("⚠️ 로컬 모드로 계속 진행합니다...")
        db = None
    
    # Data Fetching
    print("\n데이터 수집 중 (M7 + QQQ + 금리)...")
    data = yf.download(ALL_STOCKS, period='1y', auto_adjust=False, group_by='ticker', progress=False)
    
    if data.empty:
        print("❌ 데이터 다운로드 실패. 인터넷 연결을 확인하세요.")
        return
    
    # ========================================================================
    # STEP 1: Market Filters (거시경제)
    # ========================================================================
    print("\n" + "="*70)
    print("[1차 필터] 거시경제 분석 (QQQ + 금리)")
    print("="*70)
    
    qqq = data['QQQ'][['Close']].copy()
    qqq['MA120'] = qqq['Close'].rolling(window=120).mean()
    qqq_price = qqq['Close'].iloc[-1]
    qqq_ma120 = qqq['MA120'].iloc[-1]
    qqq_prev_close = qqq['Close'].iloc[-2]
    
    is_market_uptrend = qqq_price > qqq_ma120
    daily_return = (qqq_price - qqq_prev_close) / qqq_prev_close * 100
    is_market_crash = daily_return < -3.0
    
    tnx = data['^TNX'][['Close']].copy()
    tnx_price = tnx['Close'].iloc[-1]
    tnx_prev = tnx['Close'].iloc[-2]
    tnx_change = (tnx_price - tnx_prev) / tnx_prev * 100
    tnx_spike = tnx_change > 5.0
    
    market_blocked = (not is_market_uptrend) or tnx_spike
    
    if is_market_crash:
        market_status = "🚨 시장 급락 (Crash)"
    elif tnx_spike:
        market_status = "🚨 금리 급등 (Rate Spike)"
    elif not is_market_uptrend:
        market_status = "⚠️ 하락장 (Downtrend)"
    else:
        market_status = "✅ 안전 (Safe)"
    
    print(f"시장 상태: {market_status}")
    print(f"QQQ: ${qqq_price:.2f} (120일선: ${qqq_ma120:.2f})")
    print(f"금리(^TNX): {tnx_price:.2f}% (전일 대비: {tnx_change:+.2f}%)")
    
    # ========================================================================
    # STEP 2-5: Individual Stock Analysis
    # ========================================================================
    results = []
    strong_buy_list = []
    
    for group_name, group_info in GROUPS.items():
        buy_th = group_info['buy_rsi']
        sell_th = group_info['sell_rsi']
        
        for ticker in group_info['stocks']:
            print(f"\n{'='*70}")
            print(f"📊 {ticker} 분석 시작 (그룹 {group_name})")
            print(f"{'='*70}")
            
            if ticker not in data.columns:
                print(f"⚠️ {ticker} 데이터 없음. 건너뜀.")
                continue
                
            df = data[ticker][['Close']].copy()
            
            # ================================================================
            # STEP 2: 차트 기술 필터 (RSI + 이평선)
            # ================================================================
            print(f"[2차 필터] 차트 기술 분석...")
            
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA60'] = df['Close'].rolling(window=60).mean()
            
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            current_price = df['Close'].iloc[-1]
            current_rsi = df['RSI'].iloc[-1]
            ma20 = df['MA20'].iloc[-1]
            ma60 = df['MA60'].iloc[-1]
            
            is_golden_cross = ma20 > ma60
            step2_pass = current_rsi < buy_th and is_golden_cross
            
            if step2_pass:
                print(f"  ✅ 차트 필터 통과 (RSI: {current_rsi:.1f} < {buy_th}, 골든크로스)")
            else:
                print(f"  ❌ 차트 필터 미통과 (RSI: {current_rsi:.1f}, 골든크로스: {is_golden_cross})")
            
            # ================================================================
            # STEP 3: 뉴스 감성 필터
            # ================================================================
            sentiment_score = 0
            sentiment_label = "중립"
            news_block = False
            
            if step2_pass and not market_blocked:
                print(f"[3차 필터] 뉴스 감성 분석...")
                try:
                    stock = yf.Ticker(ticker)
                    news = stock.news
                    
                    if news and len(news) > 0:
                        scores = []
                        for item in news[:3]:
                            title = item.get('title', '')
                            if title:
                                vs = analyzer.polarity_scores(title)
                                scores.append(vs['compound'])
                        
                        if scores:
                            sentiment_score = sum(scores) / len(scores)
                            
                            if sentiment_score <= -0.5:
                                sentiment_label = "🔴 악재"
                                news_block = True
                                print(f"  ❌ 뉴스 필터 차단 (감성: {sentiment_score:.2f})")
                            elif sentiment_score >= 0.5:
                                sentiment_label = "🟢 호재"
                                print(f"  ✅ 뉴스 필터 통과 (감성: {sentiment_score:.2f})")
                            else:
                                sentiment_label = "⚪ 중립"
                                print(f"  ✅ 뉴스 필터 통과 (감성: {sentiment_score:.2f})")
                except Exception as e:
                    print(f"  ⚠️ 뉴스 분석 실패: {e}")
                    sentiment_label = "분석 실패"
            
            # ================================================================
            # STEP 4: 옵션 데이터 필터
            # ================================================================
            options_data = None
            options_pass = True
            options_reason = "미적용"
            
            if step2_pass and not market_blocked and not news_block:
                print(f"[4차 필터] 옵션 데이터 분석...")
                
                try:
                    analyzer_opt = OptionsAnalyzer(ticker)
                    options_report = analyzer_opt.get_full_options_report()
                    
                    if options_report['iv_metrics'] and options_report['unusual_activity']:
                        iv_data = options_report['iv_metrics']
                        unusual_data = options_report['unusual_activity']
                        
                        options_data = {
                            'iv_rank': iv_data['iv_rank'],
                            'iv_status': iv_data['iv_status'],
                            'current_iv': iv_data['current_iv'],
                            'unusual_signal': unusual_data['signal'],
                            'unusual_confidence': unusual_data['confidence'],
                            'pc_ratio': unusual_data['pc_ratio'],
                            'flow_details': unusual_data['details']
                        }
                        
                        fail_reasons = []
                        
                        if iv_data['iv_rank'] > 30:
                            fail_reasons.append(f"IV Rank 높음 ({iv_data['iv_rank']}%)")
                        
                        if 'Bearish' in unusual_data['signal']:
                            fail_reasons.append(f"Bearish Flow 감지")
                        
                        if fail_reasons:
                            options_pass = False
                            options_reason = " | ".join(fail_reasons)
                            print(f"  ❌ 옵션 필터 미통과: {options_reason}")
                        else:
                            print(f"  ✅ 옵션 필터 통과 (IV Rank: {iv_data['iv_rank']}%, Flow: {unusual_data['signal']})")
                    else:
                        print(f"  ⚠️ 옵션 데이터 부족 - 기본 통과")
                        options_data = None
                        
                except Exception as e:
                    print(f"  ⚠️ 옵션 분석 실패: {e} - 기본 통과")
            
            # ================================================================
            # STEP 5: 지지/저항선 필터 (SrVolumeFilter 사용)
            # ================================================================
            support_data = None
            support_pass = True
            support_reason = "미적용"
            
            if step2_pass and not market_blocked and not news_block and options_pass:
                print(f"[5차 필터] 지지/저항선 분석...")
                
                try:
                    sr_filter = SrVolumeFilter(df, order=5)
                    support_check = sr_filter.check_support_proximity(current_price, threshold_pct=3.0)
                    
                    support_data = {
                        'nearest_support': support_check['nearest_support'],
                        'distance_pct': support_check['distance_pct']
                    }
                    
                    support_pass = support_check['pass']
                    support_reason = support_check['reason']
                    
                    if support_pass:
                        print(f"  ✅ 지지선 필터 통과: {support_reason}")
                    else:
                        print(f"  ❌ 지지선 필터 미통과: {support_reason}")
                        
                except Exception as e:
                    print(f"  ⚠️ 지지선 분석 실패: {e} - 기본 통과")
            
            # ================================================================
            # Final Signal Determination
            # ================================================================
            signal = "관망 (Hold)"
            signal_color = "black"
            
            if market_blocked:
                signal = "매수 금지 (Market)"
                signal_color = "gray"
            elif news_block:
                signal = "악재 차단 (News)"
                signal_color = "brown"
            elif not options_pass:
                signal = "관망 (Options)"
                signal_color = "orange"
            elif not support_pass:
                signal = "관망 (Support)"
                signal_color = "darkorange"
            elif step2_pass:
                signal = "🚀 강력 매수 (STRONG BUY)"
                signal_color = "green"
                strong_buy_list.append({
                    'ticker': ticker,
                    'price': current_price,
                    'rsi': current_rsi,
                    'sentiment': sentiment_label,
                    'options_data': options_data,
                    'support_data': support_data
                })
                print(f"\n🎯 {ticker} - 5중 필터 모두 통과! STRONG BUY 확정!")
            elif current_rsi > sell_th:
                signal = "매도 (SELL)"
                signal_color = "red"
            
            # ================================================================
            # Save to Cloud DB
            # ================================================================
            if db:
                filters_passed = {
                    'market': 'pass' if not market_blocked else 'fail',
                    'chart': 'pass' if step2_pass else 'fail',
                    'news': 'pass' if not news_block else 'fail',
                    'options': 'pass' if options_pass else 'fail',
                    'support': 'pass' if support_pass else 'fail'
                }
                
                try:
                    db.log_signal(ticker, signal, current_price, filters_passed)
                except Exception as e:
                    print(f"  ⚠️ DB 저장 실패: {e}")
            
            results.append({
                'group': group_name,
                'ticker': ticker,
                'price': current_price,
                'rsi': current_rsi,
                'signal': signal,
                'signal_color': signal_color
            })
    
    # ========================================================================
    # Telegram Notification
    # ========================================================================
    if strong_buy_list:
        print(f"\n{'='*70}")
        print(f"🚀 강력 매수 신호 {len(strong_buy_list)}개 발견! 텔레그램 전송 중...")
        print(f"{'='*70}")
        
        telegram_msg = f"🤖 <b>M7 Bot V2 (Cloud)</b>\n\n"
        telegram_msg += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        telegram_msg += f"🚀 <b>강력 매수 신호 ({len(strong_buy_list)}개)</b>\n\n"
        
        for item in strong_buy_list:
            telegram_msg += f"━━━━━━━━━━━━━━━━━\n"
            telegram_msg += f"• <b>{item['ticker']}</b>\n"
            telegram_msg += f"  💰 가격: ${item['price']:.2f}\n"
            telegram_msg += f"  📊 RSI: {item['rsi']:.1f}\n"
            telegram_msg += f"  📰 뉴스: {item['sentiment']}\n"
            
            if item['options_data']:
                opt = item['options_data']
                telegram_msg += f"\n  <b>📊 옵션 데이터</b>\n"
                telegram_msg += f"  🔹 IV Rank: {opt['iv_rank']}% {opt['iv_status']}\n"
                telegram_msg += f"  🔹 Flow: {opt['unusual_signal']} ({opt['unusual_confidence']}%)\n"
                telegram_msg += f"  🔹 P/C Ratio: {opt['pc_ratio']}\n"
            
            if item['support_data'] and item['support_data']['nearest_support']:
                sup = item['support_data']
                telegram_msg += f"\n  <b>📍 지지선</b>\n"
                telegram_msg += f"  🔹 가장 가까운 지지선: ${sup['nearest_support']:.2f}\n"
                telegram_msg += f"  🔹 거리: {sup['distance_pct']:.1f}%\n"
            
            telegram_msg += f"\n  ✅ <b>5중 필터 모두 통과!</b>\n\n"
        
        telegram_msg += f"━━━━━━━━━━━━━━━━━\n"
        telegram_msg += f"시장 상태: {market_status}\n"
        telegram_msg += f"금리: {tnx_price:.2f}% ({tnx_change:+.2f}%)"
        
        try:
            asyncio.run(send_telegram_message(telegram_msg))
            print("✅ 텔레그램 전송 완료!")
        except Exception as e:
            print(f"❌ 텔레그램 전송 실패: {e}")
    else:
        print(f"\n{'='*70}")
        print("📭 강력 매수 신호 없음. 텔레그램 전송 생략.")
        print(f"{'='*70}")
    
    print(f"\n{'='*70}")
    print("✅ M7 Bot V2 (Cloud) 실행 완료!")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
