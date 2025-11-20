"""
M7 Bot - Main Signal Engine
Core analysis engine integrating 5-layer filtering, cloud DB storage, and Telegram notifications.
"""

import os
import sys
import json
import asyncio
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Union
from dotenv import load_dotenv
from telegram import Bot
from telegram.request import HTTPXRequest
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Custom Modules
from m7_cloud import DBManager
from m7_core import SrVolumeFilter

# Load environment variables
load_dotenv()

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore
        sys.stderr.reconfigure(encoding='utf-8')  # type: ignore
    except Exception:
        pass

# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, 'config.json')

try:
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        CONFIG = json.load(f)
    BOT_TOKEN: str = CONFIG['telegram']['bot_token']
    CHAT_ID: str = CONFIG['telegram']['chat_id']
except FileNotFoundError:
    print("⚠️ config.json 파일을 찾을 수 없습니다. 텔레그램 기능이 제한될 수 있습니다.")
    BOT_TOKEN = ""
    CHAT_ID = ""

# Stock Groups Configuration
GROUPS: Dict[str, Dict[str, Any]] = {
    'A': {'stocks': ['NVDA', 'TSLA'], 'buy_rsi': 25, 'sell_rsi': 65, 'desc': '고변동성'},
    'B': {'stocks': ['META', 'AMZN', 'GOOGL'], 'buy_rsi': 30, 'sell_rsi': 70, 'desc': '중변동성'},
    'C': {'stocks': ['AAPL', 'MSFT'], 'buy_rsi': 35, 'sell_rsi': 75, 'desc': '저변동성'}
}

ALL_STOCKS: List[str] = []
for g in GROUPS.values():
    ALL_STOCKS.extend(g['stocks'])
ALL_STOCKS.extend(['QQQ', '^TNX'])

# Initialize Sentiment Analyzer
ANALYZER = SentimentIntensityAnalyzer()


# ============================================================================
# CLASS: OPTIONS ANALYZER
# ============================================================================
class OptionsAnalyzer:
    """
    야후 파이낸스 데이터를 기반으로 옵션 내재 변동성(IV) 및 수급을 분석하는 클래스
    """
    
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.ticker = yf.Ticker(symbol)
        
    def get_iv_metrics(self, lookback_days: int = 252) -> Optional[Dict[str, Any]]:
        """
        IV Rank 및 Percentile 계산
        
        Args:
            lookback_days (int): 과거 데이터 조회 기간 (기본값: 252일)
            
        Returns:
            Optional[Dict[str, Any]]: IV 관련 메트릭. 실패 시 None.
        """
        try:
            expirations = self.ticker.options
            if not expirations:
                return None
            
            target_expiry = self._get_target_expiration(expirations)
            opt_chain = self.ticker.option_chain(target_expiry)
            
            # 현재 주가 및 ATM 옵션 찾기
            hist = self.ticker.history(period='1d')
            if hist.empty:
                return None
            current_price = hist['Close'].iloc[-1]
            
            calls = opt_chain.calls
            calls['distance'] = abs(calls['strike'] - current_price)
            atm_call = calls.loc[calls['distance'].idxmin()]
            
            current_iv = atm_call['impliedVolatility']
            hist_ivs = self._get_historical_iv(lookback_days)
            
            # IV Rank 계산
            if hist_ivs is not None and len(hist_ivs) > 0:
                iv_min = hist_ivs.min()
                iv_max = hist_ivs.max()
                
                if iv_max - iv_min > 0:
                    iv_rank = ((current_iv - iv_min) / (iv_max - iv_min)) * 100
                    iv_rank = max(0, min(100, iv_rank))
                else:
                    iv_rank = 50.0
            else:
                iv_rank = 50.0
            
            # 상태 결정
            if iv_rank < 30:
                iv_status = "Low 🟢"
            elif iv_rank < 70:
                iv_status = "Medium 🟡"
            else:
                iv_status = "High 🔴"
            
            return {
                'current_iv': round(current_iv * 100, 2),
                'iv_rank': round(iv_rank, 2),
                'iv_status': iv_status
            }
            
        except Exception as e:
            print(f"  ⚠️ IV 데이터 수집 실패 ({self.symbol}): {e}")
            return None
    
    def detect_unusual_activity(self) -> Optional[Dict[str, Any]]:
        """
        비정상 옵션 활동(Unusual Options Activity) 감지
        
        Returns:
            Optional[Dict[str, Any]]: 분석 결과 (Signal, Confidence, Details)
        """
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
            
            pc_ratio = put_volume / call_volume if call_volume > 0 else 999.0
            
            # 간단한 로직: P/C Ratio 기반 점수화
            bullish_score = 0
            bearish_score = 0
            details = []
            
            if pc_ratio < 0.7:
                bullish_score += 50
                details.append(f"Call 우세 (P/C: {pc_ratio:.2f})")
            elif pc_ratio > 1.3:
                bearish_score += 50
                details.append(f"Put 우세 (P/C: {pc_ratio:.2f})")
            
            # 결과 종합
            if bullish_score > bearish_score:
                signal = "Bullish 🐂"
                confidence = bullish_score
            elif bearish_score > bullish_score:
                signal = "Bearish 🐻"
                confidence = bearish_score
            else:
                signal = "Neutral ⚖️"
                confidence = 50
                
            return {
                'signal': signal,
                'confidence': confidence,
                'pc_ratio': round(pc_ratio, 2),
                'details': " | ".join(details) if details else "특이사항 없음"
            }
            
        except Exception as e:
            print(f"  ⚠️ Unusual Activity 감지 실패 ({self.symbol}): {e}")
            return None
    
    def _get_target_expiration(self, expirations: tuple) -> str:
        """30-45일 사이 만기 선택 (없으면 첫 번째)"""
        target_days = 37
        min_diff = 999
        target = expirations[0]
        
        for exp in expirations[:4]:
            try:
                exp_date = datetime.strptime(exp, '%Y-%m-%d')
                days = (exp_date - datetime.now()).days
                
                if 20 <= days <= 60:
                    diff = abs(days - target_days)
                    if diff < min_diff:
                        min_diff = diff
                        target = exp
            except ValueError:
                continue
        return target
    
    def _get_historical_iv(self, lookback_days: int) -> Optional[pd.Series]:
        """과거 변동성(HV) 계산으로 IV 근사"""
        try:
            hist = self.ticker.history(period=f"{lookback_days}d")
            if len(hist) < 30:
                return None
            hist['log_return'] = np.log(hist['Close'] / hist['Close'].shift(1))
            hist['hv_30'] = hist['log_return'].rolling(window=30).std() * np.sqrt(252)
            return hist['hv_30'].dropna()
        except Exception:
            return None


# ============================================================================
# CORE FUNCTIONS
# ============================================================================
def analyze_market_condition(data: pd.DataFrame) -> Tuple[bool, str, float, float]:
    """
    1차 필터: 거시경제 분석 (QQQ 추세 + TNX 금리)
    
    Returns:
        Tuple[bool, str, float, float]: (차단여부, 상태메시지, 금리, 금리변동폭)
    """
    print("\n" + "="*70)
    print("[1차 필터] 거시경제 분석 (QQQ + 금리)")
    print("="*70)
    
    # QQQ Analysis
    qqq = data['QQQ'][['Close']].copy()
    qqq['MA120'] = qqq['Close'].rolling(window=120).mean()
    
    qqq_price = float(qqq['Close'].iloc[-1])
    qqq_ma120 = float(qqq['MA120'].iloc[-1])
    qqq_prev = float(qqq['Close'].iloc[-2])
    
    is_uptrend = qqq_price > qqq_ma120
    daily_return = (qqq_price - qqq_prev) / qqq_prev * 100
    is_crash = daily_return < -3.0
    
    # TNX Analysis
    tnx = data['^TNX'][['Close']].copy()
    tnx_price = float(tnx['Close'].iloc[-1])
    tnx_prev = float(tnx['Close'].iloc[-2])
    tnx_change = (tnx_price - tnx_prev) / tnx_prev * 100
    tnx_spike = tnx_change > 5.0
    
    # Decision
    blocked = (not is_uptrend) or tnx_spike or is_crash
    
    if is_crash:
        status = "🚨 시장 급락 (Crash)"
    elif tnx_spike:
        status = "🚨 금리 급등 (Rate Spike)"
    elif not is_uptrend:
        status = "⚠️ 하락장 (Downtrend)"
    else:
        status = "✅ 안전 (Safe)"
        
    print(f"시장 상태: {status}")
    print(f"QQQ: ${qqq_price:.2f} (120일선: ${qqq_ma120:.2f})")
    print(f"금리(^TNX): {tnx_price:.2f}% (변동: {tnx_change:+.2f}%)")
    
    return blocked, status, tnx_price, tnx_change


def analyze_stock(
    ticker: str, 
    data: pd.DataFrame, 
    group_info: Dict[str, Any], 
    market_blocked: bool
) -> Dict[str, Any]:
    """
    개별 종목에 대한 5단계 필터링 수행
    """
    print(f"\n📊 {ticker} 분석 시작 ({group_info['desc']})")
    
    # Init results
    result = {
        'ticker': ticker,
        'price': 0.0,
        'rsi': 0.0,
        'signal': "관망 (Hold)",
        'signal_type': "HOLD",
        'filters': {},
        'details': {}
    }
    
    try:
        df = data[ticker][['Close']].copy()
        current_price = float(df['Close'].iloc[-1])
        result['price'] = current_price
        
        # [Step 2] Chart Filter
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        current_rsi = float(df['RSI'].iloc[-1])
        result['rsi'] = current_rsi
        
        is_golden_cross = df['MA20'].iloc[-1] > df['MA60'].iloc[-1]
        step2_pass = current_rsi < group_info['buy_rsi'] and is_golden_cross
        
        print(f"  [차트] RSI: {current_rsi:.1f}, GC: {is_golden_cross} -> {'✅' if step2_pass else '❌'}")
        
        # [Step 3] News Filter
        sentiment_label = "중립"
        news_blocked = False
        if step2_pass and not market_blocked:
            try:
                stock_obj = yf.Ticker(ticker)
                news = stock_obj.news
                scores = []
                if news:
                    for item in news[:3]:
                        title = item.get('title', '')
                        scores.append(ANALYZER.polarity_scores(title)['compound'])
                    
                    if scores:
                        avg_score = sum(scores) / len(scores)
                        if avg_score <= -0.5:
                            sentiment_label = "🔴 악재"
                            news_blocked = True
                        elif avg_score >= 0.5:
                            sentiment_label = "🟢 호재"
                        
            except Exception as e:
                print(f"  ⚠️ 뉴스 분석 오류: {e}")
        
        result['details']['sentiment'] = sentiment_label
        
        # [Step 4] Options Filter
        options_pass = True
        options_data = None
        if step2_pass and not market_blocked and not news_blocked:
            analyzer_opt = OptionsAnalyzer(ticker)
            iv_metrics = analyzer_opt.get_iv_metrics()
            activity = analyzer_opt.detect_unusual_activity()
            
            if iv_metrics and activity:
                options_data = {**iv_metrics, **activity}
                result['details']['options'] = options_data
                
                if iv_metrics['iv_rank'] > 30 or 'Bearish' in activity['signal']:
                    options_pass = False
                    print(f"  [옵션] IV/Flow 부적합 -> ❌")
                else:
                    print(f"  [옵션] IV: {iv_metrics['iv_rank']}% -> ✅")
        
        # [Step 5] Support Filter
        support_pass = True
        support_data = None
        if step2_pass and not market_blocked and not news_blocked and options_pass:
            try:
                sr_filter = SrVolumeFilter(df, order=5)
                check = sr_filter.check_support_proximity(current_price, threshold_pct=3.0)
                support_pass = check['pass']
                support_data = {
                    'nearest_support': check['nearest_support'],
                    'distance_pct': check['distance_pct']
                }
                result['details']['support'] = support_data
                print(f"  [지지선] {check['reason']} -> {'✅' if support_pass else '❌'}")
            except Exception:
                pass

        # Final Signal Logic
        if market_blocked:
            result['signal'] = "매수 금지 (Market)"
            result['signal_type'] = "MARKET_BLOCK"
        elif news_blocked:
            result['signal'] = "악재 차단 (News)"
            result['signal_type'] = "NEWS_BLOCK"
        elif not options_pass:
            result['signal'] = "관망 (Options)"
            result['signal_type'] = "OPTIONS_WAIT"
        elif not support_pass:
            result['signal'] = "관망 (Support)"
            result['signal_type'] = "SUPPORT_WAIT"
        elif step2_pass:
            result['signal'] = "🚀 강력 매수 (STRONG BUY)"
            result['signal_type'] = "STRONG BUY"
        elif current_rsi > group_info['sell_rsi']:
            result['signal'] = "매도 (SELL)"
            result['signal_type'] = "SELL"
            
        # Filter Results
        result['filters'] = {
            'market': 'fail' if market_blocked else 'pass',
            'chart': 'pass' if step2_pass else 'fail',
            'news': 'fail' if news_blocked else 'pass',
            'options': 'pass' if options_pass else 'fail',
            'support': 'pass' if support_pass else 'fail'
        }
        
        return result

    except Exception as e:
        print(f"  ❌ 분석 중 치명적 오류: {e}")
        return result


async def send_telegram_report(
    strong_buy_list: List[Dict[str, Any]], 
    market_status: str, 
    tnx_info: Tuple[float, float]
) -> None:
    """텔레그램 리포트 전송"""
    if not BOT_TOKEN or not CHAT_ID:
        return

    print(f"\n🚀 강력 매수 신호 {len(strong_buy_list)}개 전송 중...")
    
    msg = f"🤖 <b>M7 Bot V2 (Cloud)</b>\n"
    msg += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    
    if strong_buy_list:
        msg += f"🚀 <b>강력 매수 신호 ({len(strong_buy_list)}개)</b>\n\n"
        for item in strong_buy_list:
            msg += f"━━━━━━━━━━━━━━━━━\n"
            msg += f"• <b>{item['ticker']}</b> (${item['price']:.2f})\n"
            msg += f"  📊 RSI: {item['rsi']:.1f}\n"
            
            details = item.get('details', {})
            if 'options' in details and details['options']:
                opt = details['options']
                msg += f"  🔹 IV Rank: {opt['iv_rank']}%\n"
                msg += f"  🔹 Flow: {opt['signal']}\n"
            
            if 'support' in details and details['support']:
                sup = details['support']
                if sup['nearest_support']:
                    msg += f"  📍 지지선: ${sup['nearest_support']:.2f} ({sup['distance_pct']:.1f}%)\n"
    else:
        msg += "📭 <b>강력 매수 신호 없음</b>\n\n"
        msg += "━━━━━━━━━━━━━━━━━\n"

    msg += f"\n시장 상태: {market_status}\n"
    msg += f"금리(^TNX): {tnx_info[0]:.2f}% ({tnx_info[1]:+.2f}%)"

    try:
        request = HTTPXRequest(connection_pool_size=8, connect_timeout=20.0, read_timeout=30.0)
        bot = Bot(token=BOT_TOKEN, request=request)
        await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='HTML')
        print("✅ 텔레그램 전송 성공")
    except Exception as e:
        print(f"❌ 텔레그램 전송 실패: {e}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================
def main() -> None:
    print("="*70)
    print("🚀 M7 Bot - SaaS Cloud Version (V2)")
    print("="*70)

    # 1. DB Connection
    try:
        db = DBManager()
        print("✅ Supabase 연결 성공!")
    except Exception as e:
        print(f"❌ Supabase 연결 실패: {e}")
        db = None

    # 2. Data Fetching
    print("\n데이터 수집 중...")
    data = yf.download(ALL_STOCKS, period='1y', auto_adjust=False, group_by='ticker', progress=False)
    if data.empty:
        print("❌ 데이터 다운로드 실패.")
        return

    # 3. Market Analysis
    market_blocked, market_status, tnx_price, tnx_change = analyze_market_condition(data)

    # 4. Individual Stock Analysis
    strong_buy_list = []
    
    for group_name, group_info in GROUPS.items():
        for ticker in group_info['stocks']:
            if ticker not in data.columns:
                continue
                
            result = analyze_stock(ticker, data, group_info, market_blocked)
            
            # Log to DB
            if db:
                db.log_signal(
                    ticker, 
                    result['signal'], 
                    result['price'], 
                    result['filters']
                )
            
            if "STRONG BUY" in result['signal_type']:
                strong_buy_list.append(result)

    # 5. Telegram Notification
    if strong_buy_list:
        asyncio.run(send_telegram_report(strong_buy_list, market_status, (tnx_price, tnx_change)))
    else:
        print("\n📭 강력 매수 신호가 없어 알림을 보내지 않습니다.")

    print("\n✅ 모든 작업 완료.")


if __name__ == "__main__":
    main()
