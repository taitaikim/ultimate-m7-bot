import yfinance as yf
import pandas as pd
import numpy as np
import os
import sys
import webbrowser
import json
from datetime import datetime, timedelta
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from scipy.signal import argrelextrema
import asyncio
from telegram import Bot
from performance_tracker import PerformanceTracker

# Fix Windows console encoding for Korean and emojis
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

# --- Configuration ---
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(os.path.dirname(script_dir), 'config.json')
output_html = os.path.join(script_dir, 'ultimate_report.html')

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
ALL_STOCKS.extend(['QQQ', '^TNX'])  # Add QQQ and 10-Year Treasury

# Sentiment Analyzer
analyzer = SentimentIntensityAnalyzer()


# ============================================================================
# OPTIONS ANALYZER CLASS
# ============================================================================
class OptionsAnalyzer:
    """
    M7 종목의 옵션 데이터 분석
    - IV Rank/Percentile 계산
    - Unusual Options Activity 감지
    """
    
    def __init__(self, symbol):
        self.symbol = symbol
        self.ticker = yf.Ticker(symbol)
        
    def get_iv_metrics(self, lookback_days=252):
        """
        IV Rank 및 IV Percentile 계산
        
        Returns:
            dict: {
                'current_iv': float,
                'iv_rank': float (0-100),
                'iv_percentile': float (0-100),
                'iv_status': str ('Low'/'Medium'/'High')
            }
        """
        try:
            # 옵션 체인 가져오기
            expirations = self.ticker.options
            if not expirations:
                return None
            
            # 30-45일 만기 옵션 선택 (ATM 옵션)
            target_expiry = self._get_target_expiration(expirations)
            opt_chain = self.ticker.option_chain(target_expiry)
            
            # ATM 옵션 IV 추출
            current_price = self.ticker.history(period='1d')['Close'].iloc[-1]
            
            # Call과 Put 중 ATM에 가까운 것 찾기
            calls = opt_chain.calls
            calls['distance'] = abs(calls['strike'] - current_price)
            atm_call = calls.loc[calls['distance'].idxmin()]
            
            current_iv = atm_call['impliedVolatility']
            
            # 과거 IV 데이터 수집 (역사적 비교)
            hist_ivs = self._get_historical_iv(lookback_days)
            
            if hist_ivs is not None and len(hist_ivs) > 0:
                # IV Rank = (현재 IV - 최저 IV) / (최고 IV - 최저 IV) * 100
                iv_min = hist_ivs.min()
                iv_max = hist_ivs.max()
                
                # Avoid division by zero
                if iv_max - iv_min > 0:
                    iv_rank = ((current_iv - iv_min) / (iv_max - iv_min)) * 100
                    # Clamp to 0-100 range (in case current IV is outside historical range)
                    iv_rank = max(0, min(100, iv_rank))
                else:
                    iv_rank = 50.0
                
                # IV Percentile = 현재 IV보다 낮은 날의 비율
                iv_percentile = (hist_ivs < current_iv).sum() / len(hist_ivs) * 100
            else:
                # 과거 데이터 없으면 현재 값만 사용
                iv_rank = 50.0
                iv_percentile = 50.0
            
            # IV 상태 판정
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
        """
        Unusual Options Activity 감지
        - Put/Call Ratio 분석
        - 볼륨 vs OI 비율
        - 대형 거래 감지
        
        Returns:
            dict: {
                'signal': str ('Bullish'/'Bearish'/'Neutral'),
                'confidence': float (0-100),
                'details': str
            }
        """
        try:
            expirations = self.ticker.options
            if not expirations:
                return None
            
            # 가장 가까운 만기 선택
            near_expiry = expirations[0]
            opt_chain = self.ticker.option_chain(near_expiry)
            
            calls = opt_chain.calls
            puts = opt_chain.puts
            
            # 1. Put/Call Volume Ratio
            call_volume = calls['volume'].sum()
            put_volume = puts['volume'].sum()
            
            if call_volume == 0:
                pc_ratio = 999
            else:
                pc_ratio = put_volume / call_volume
            
            # 2. Volume vs Open Interest (신규 포지션 감지)
            calls['vol_oi_ratio'] = calls['volume'] / (calls['openInterest'] + 1)
            puts['vol_oi_ratio'] = puts['volume'] / (puts['openInterest'] + 1)
            
            # 높은 Vol/OI 비율 = Unusual Activity
            unusual_calls = calls[calls['vol_oi_ratio'] > 2.0]
            unusual_puts = puts[puts['vol_oi_ratio'] > 2.0]
            
            # 3. 대형 거래 감지 (상위 10% 거래량)
            call_volume_threshold = calls['volume'].quantile(0.9)
            put_volume_threshold = puts['volume'].quantile(0.9)
            
            large_calls = calls[calls['volume'] > call_volume_threshold]
            large_puts = puts[puts['volume'] > put_volume_threshold]
            
            # 신호 판정
            bullish_score = 0
            bearish_score = 0
            details = []
            
            # Put/Call Ratio 평가
            if pc_ratio < 0.7:
                bullish_score += 30
                details.append(f"Call 우세 (P/C: {pc_ratio:.2f})")
            elif pc_ratio > 1.3:
                bearish_score += 30
                details.append(f"Put 우세 (P/C: {pc_ratio:.2f})")
            
            # Unusual Activity 평가
            if len(unusual_calls) > len(unusual_puts):
                bullish_score += 25
                details.append(f"Call Unusual ({len(unusual_calls)}건)")
            elif len(unusual_puts) > len(unusual_calls):
                bearish_score += 25
                details.append(f"Put Unusual ({len(unusual_puts)}건)")
            
            # 대형 거래 평가
            large_call_value = (large_calls['volume'] * large_calls['lastPrice']).sum()
            large_put_value = (large_puts['volume'] * large_puts['lastPrice']).sum()
            
            if large_call_value > large_put_value * 1.5:
                bullish_score += 25
                details.append(f"대형 Call 매수")
            elif large_put_value > large_call_value * 1.5:
                bearish_score += 25
                details.append(f"대형 Put 매수")
            
            # 최종 신호 결정
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
        
        for exp in expirations[:4]:  # 가까운 4개만 체크
            exp_date = datetime.strptime(exp, '%Y-%m-%d')
            days = (exp_date - datetime.now()).days
            
            if 20 <= days <= 60:
                diff = abs(days - target_days)
                if diff < min_diff:
                    min_diff = diff
                    target = exp
        
        return target
    
    def _get_historical_iv(self, lookback_days):
        """
        과거 IV 데이터 수집 (간접 계산)
        실제로는 역사적 변동성(HV)을 사용
        """
        try:
            # 과거 가격 데이터
            hist = self.ticker.history(period=f"{lookback_days}d")
            
            # 로그 수익률 계산
            hist['log_return'] = np.log(hist['Close'] / hist['Close'].shift(1))
            
            # 30일 rolling 변동성 (연율화)
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
# SUPPORT/RESISTANCE ANALYZER
# ============================================================================
def calculate_support_resistance(df, order=5):
    """
    지지선/저항선 계산 (Local Extrema 방식)
    
    Args:
        df: 가격 데이터프레임 (Close 컬럼 필요)
        order: 극값 탐지 범위 (기본 5일)
    
    Returns:
        dict: {'support': [prices], 'resistance': [prices]}
    """
    try:
        # Local minima (지지선)
        local_min_idx = argrelextrema(df['Close'].values, np.less, order=order)[0]
        support_levels = df['Close'].iloc[local_min_idx].values
        
        # Local maxima (저항선)
        local_max_idx = argrelextrema(df['Close'].values, np.greater, order=order)[0]
        resistance_levels = df['Close'].iloc[local_max_idx].values
        
        # 최근 6개월 데이터만 사용 (더 관련성 높음)
        recent_cutoff = len(df) - 120  # 약 6개월
        support_levels = [s for i, s in zip(local_min_idx, support_levels) if i > recent_cutoff]
        resistance_levels = [r for i, r in zip(local_max_idx, resistance_levels) if i > recent_cutoff]
        
        return {
            'support': sorted(support_levels),
            'resistance': sorted(resistance_levels, reverse=True)
        }
    except Exception as e:
        print(f"  ⚠️ 지지/저항선 계산 실패: {e}")
        return {'support': [], 'resistance': []}


def find_nearest_support(current_price, support_levels):
    """
    현재가 아래의 가장 가까운 지지선 찾기
    
    Args:
        current_price: 현재 주가
        support_levels: 지지선 리스트
    
    Returns:
        float or None: 가장 가까운 지지선 가격
    """
    if not support_levels:
        return None
    
    # 현재가보다 낮은 지지선만 필터링
    below_supports = [s for s in support_levels if s < current_price]
    
    if not below_supports:
        return None
    
    # 가장 가까운 것 선택
    return max(below_supports)


def check_support_filter(current_price, nearest_support, threshold_pct=3.0):
    """
    5차 필터: 지지선 근접도 체크
    
    Args:
        current_price: 현재 주가
        nearest_support: 가장 가까운 지지선
        threshold_pct: 허용 범위 (기본 3%)
    
    Returns:
        dict: {'pass': bool, 'distance_pct': float, 'reason': str}
    """
    if nearest_support is None:
        return {
            'pass': True,  # 지지선 없으면 통과 (데이터 부족)
            'distance_pct': None,
            'reason': '지지선 데이터 없음 (기본 통과)'
        }
    
    # 현재가와 지지선 사이 거리 (%)
    distance_pct = ((current_price - nearest_support) / nearest_support) * 100
    
    if distance_pct <= threshold_pct:
        return {
            'pass': True,
            'distance_pct': round(distance_pct, 2),
            'reason': f'지지선 근접 ({distance_pct:.1f}% 이내)'
        }
    else:
        return {
            'pass': False,
            'distance_pct': round(distance_pct, 2),
            'reason': f'지지선에서 멀리 떨어짐 ({distance_pct:.1f}%)'
        }


# ============================================================================
# DATA FETCHING
# ============================================================================
print("="*70)
print("🚀 Ultimate M7 Bot - 5중 필터 시스템")
print("="*70)
print("\n데이터 수집 중 (M7 + QQQ + 금리)...")
data = yf.download(ALL_STOCKS, period='1y', auto_adjust=False, group_by='ticker', progress=False)

if data.empty:
    print("❌ 데이터 다운로드 실패. 인터넷 연결을 확인하세요.")
    exit()

# Initialize Performance Tracker
tracker = PerformanceTracker()
print("📊 성과 추적 시스템 활성화")


# ============================================================================
# STEP 1: Market Filters (거시경제)
# ============================================================================
print("\n" + "="*70)
print("[1차 필터] 거시경제 분석 (QQQ + 금리)")
print("="*70)

# Filter 1A: QQQ Trend
if 'QQQ' not in data.columns:
    print("❌ QQQ 데이터를 찾을 수 없습니다.")
    exit()

qqq = data['QQQ'][['Close']].copy()
qqq['MA120'] = qqq['Close'].rolling(window=120).mean()
qqq_price = qqq['Close'].iloc[-1]
qqq_ma120 = qqq['MA120'].iloc[-1]
qqq_prev_close = qqq['Close'].iloc[-2]

is_market_uptrend = qqq_price > qqq_ma120
daily_return = (qqq_price - qqq_prev_close) / qqq_prev_close * 100
is_market_crash = daily_return < -3.0

# Filter 1B: Interest Rate (^TNX)
if '^TNX' not in data.columns:
    print("⚠️ 금리 데이터를 찾을 수 없습니다.")
    tnx_spike = False
    tnx_price = 0
    tnx_change = 0
else:
    tnx = data['^TNX'][['Close']].copy()
    tnx_price = tnx['Close'].iloc[-1]
    tnx_prev = tnx['Close'].iloc[-2]
    tnx_change = (tnx_price - tnx_prev) / tnx_prev * 100
    tnx_spike = tnx_change > 5.0  # 5% spike

# Overall Market Status
market_blocked = (not is_market_uptrend) or tnx_spike

market_status = "✅ 안전 (Safe)"
market_color = "green"
if not is_market_uptrend:
    market_status = "⚠️ 하락장 (Downtrend)"
    market_color = "orange"
if tnx_spike:
    market_status = "🚨 금리 급등 (Rate Spike)"
    market_color = "red"
if is_market_crash:
    market_status = "🚨 시장 급락 (Crash)"
    market_color = "darkred"

print(f"시장 상태: {market_status}")
print(f"QQQ: ${qqq_price:.2f} (120일선: ${qqq_ma120:.2f})")
print(f"금리(^TNX): {tnx_price:.2f}% (전일 대비: {tnx_change:+.2f}%)")


# ============================================================================
# STEP 2-5: Individual Stock Analysis (5중 필터)
# ============================================================================
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
        
        # ====================================================================
        # STEP 2: 차트 기술 필터 (RSI + 이평선)
        # ====================================================================
        print(f"[2차 필터] 차트 기술 분석...")
        
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Current Values
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
        
        # ====================================================================
        # STEP 3: 뉴스 감성 필터
        # ====================================================================
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
        
        # ====================================================================
        # STEP 4: 옵션 데이터 필터 ⭐ NEW
        # ====================================================================
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
                    
                    # 필터 조건 체크
                    fail_reasons = []
                    
                    # 조건 1: IV Rank <= 30
                    if iv_data['iv_rank'] > 30:
                        fail_reasons.append(f"IV Rank 높음 ({iv_data['iv_rank']}%)")
                    
                    # 조건 2: Bullish Flow
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
        
        # ====================================================================
        # STEP 5: 지지/저항선 필터 ⭐ NEW
        # ====================================================================
        support_data = None
        support_pass = True
        support_reason = "미적용"
        
        if step2_pass and not market_blocked and not news_block and options_pass:
            print(f"[5차 필터] 지지/저항선 분석...")
            
            try:
                sr_levels = calculate_support_resistance(df, order=5)
                nearest_support = find_nearest_support(current_price, sr_levels['support'])
                
                support_check = check_support_filter(current_price, nearest_support, threshold_pct=3.0)
                
                support_data = {
                    'nearest_support': nearest_support,
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
        
        # ====================================================================
        # Final Signal Determination
        # ====================================================================
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
        
        results.append({
            'group': group_name,
            'ticker': ticker,
            'price': current_price,
            'rsi': current_rsi,
            'threshold': f"{buy_th} / {sell_th}",
            'sentiment': sentiment_label,
            'options_data': options_data,
            'support_data': support_data,
            'signal': signal,
            'signal_color': signal_color
        })
        
        # Log signal to performance tracker
        filters_passed = {
            'market': 'pass' if not market_blocked else 'fail',
            'chart': 'pass' if step2_pass else 'fail',
            'news': 'pass' if not news_block else 'fail',
            'options': 'pass' if options_pass else 'fail',
            'support': 'pass' if support_pass else 'fail'
        }
        tracker.log_signal(ticker, signal, current_price, filters_passed)


# ============================================================================
# TELEGRAM NOTIFICATION
# ============================================================================
async def send_telegram_message(message):
    """텔레그램 메시지 전송 (타임아웃 및 재시도 로직 포함)"""
    from telegram.request import HTTPXRequest
    
    # 타임아웃 설정: 연결 20초, 읽기 30초
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


if strong_buy_list:
    print(f"\n{'='*70}")
    print(f"🚀 강력 매수 신호 {len(strong_buy_list)}개 발견! 텔레그램 전송 중...")
    print(f"{'='*70}")
    
    telegram_msg = f"🤖 <b>M7 봇 알림 (5중 필터)</b>\n\n"
    telegram_msg += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    telegram_msg += f"🚀 <b>강력 매수 신호 ({len(strong_buy_list)}개)</b>\n\n"
    
    for item in strong_buy_list:
        telegram_msg += f"━━━━━━━━━━━━━━━━━\n"
        telegram_msg += f"• <b>{item['ticker']}</b>\n"
        telegram_msg += f"  💰 가격: ${item['price']:.2f}\n"
        telegram_msg += f"  📊 RSI: {item['rsi']:.1f}\n"
        telegram_msg += f"  📰 뉴스: {item['sentiment']}\n"
        
        # 옵션 데이터 추가
        if item['options_data']:
            opt = item['options_data']
            telegram_msg += f"\n  <b>📊 옵션 데이터</b>\n"
            telegram_msg += f"  🔹 IV Rank: {opt['iv_rank']}% {opt['iv_status']}\n"
            telegram_msg += f"  🔹 Flow: {opt['unusual_signal']} ({opt['unusual_confidence']}%)\n"
            telegram_msg += f"  🔹 P/C Ratio: {opt['pc_ratio']}\n"
        
        # 지지선 데이터 추가
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


# ============================================================================
# HTML REPORT GENERATION
# ============================================================================
print(f"\n{'='*70}")
print("📄 HTML 리포트 생성 중...")
print(f"{'='*70}")

today_str = datetime.now().strftime('%Y년 %m월 %d일 %H:%M')

html_rows = ""
for r in results:
    # 옵션 데이터 표시
    if r['options_data']:
        opt = r['options_data']
        iv_rank_str = f"{opt['iv_rank']}%"
        flow_str = f"{opt['unusual_signal']} ({opt['unusual_confidence']}%)"
        pc_ratio_str = f"{opt['pc_ratio']}"
    else:
        iv_rank_str = "N/A"
        flow_str = "N/A"
        pc_ratio_str = "N/A"
    
    # 지지선 데이터 표시
    if r['support_data'] and r['support_data']['nearest_support']:
        support_str = f"${r['support_data']['nearest_support']:.2f}"
        distance_str = f"({r['support_data']['distance_pct']:.1f}%)"
    else:
        support_str = "N/A"
        distance_str = ""
    
    html_rows += f"""
    <tr>
        <td class="group-{r['group']}">{r['group']}</td>
        <td style="font-weight:bold;">{r['ticker']}</td>
        <td>${r['price']:.2f}</td>
        <td style="color: {'red' if r['rsi'] > 70 else 'blue' if r['rsi'] < 30 else 'black'}">{r['rsi']:.2f}</td>
        <td>{r['threshold']}</td>
        <td>{r['sentiment']}</td>
        <td>{iv_rank_str}</td>
        <td>{flow_str}</td>
        <td>{pc_ratio_str}</td>
        <td>{support_str} {distance_str}</td>
        <td style="color: {r['signal_color']}; font-weight: bold;">{r['signal']}</td>
    </tr>
    """

crash_alert = ""
if is_market_crash:
    crash_alert = """
    <div class="alert-box">
        🚨 시장 급락 경보! (QQQ -3% 이상 하락)<br>
        신규 진입은 최대 2종목까지만 제한적으로 허용하세요.
    </div>
    """

html_content = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ultimate M7 봇 리포트 (5중 필터)</title>
    <style>
        body {{ font-family: 'Malgun Gothic', sans-serif; margin: 0; padding: 20px; background-color: #f4f4f9; }}
        .container {{ max-width: 1400px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
        h1 {{ text-align: center; color: #333; }}
        .subtitle {{ text-align: center; color: #666; font-size: 1.1em; margin-bottom: 10px; }}
        .date {{ text-align: center; color: #666; margin-bottom: 20px; }}
        
        .status-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px; }}
        .status-box {{ padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; }}
        
        .alert-box {{ background-color: #ffebee; color: #c62828; padding: 15px; text-align: center; border: 2px solid #ef5350; border-radius: 10px; margin-bottom: 20px; font-weight: bold; animation: blink 2s infinite; }}
        
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; font-size: 0.9em; }}
        th, td {{ padding: 10px; border-bottom: 1px solid #ddd; text-align: center; }}
        th {{ background-color: #f8f9fa; color: #333; font-weight: bold; }}
        
        .group-A {{ color: #e91e63; font-weight: bold; }}
        .group-B {{ color: #2196f3; font-weight: bold; }}
        .group-C {{ color: #4caf50; font-weight: bold; }}
        
        .checklist-box {{ border: 2px dashed #aaa; padding: 20px; border-radius: 10px; background-color: #fff9c4; }}
        .checklist-title {{ font-weight: bold; margin-bottom: 10px; font-size: 1.1em; }}
        
        .filter-legend {{ background-color: #e3f2fd; padding: 15px; border-radius: 10px; margin-bottom: 20px; }}
        .filter-legend h3 {{ margin-top: 0; color: #1976d2; }}
        .filter-legend ul {{ margin: 5px 0; padding-left: 20px; }}
        
        @keyframes blink {{ 50% {{ opacity: 0.5; }} }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Ultimate M7 봇 종합 리포트</h1>
        <div class="subtitle">⭐ 5중 필터 시스템 (거시경제 + 뉴스 + 차트 + 옵션 + 지지선)</div>
        <div class="date">{today_str} 기준</div>
        
        <div class="filter-legend">
            <h3>📊 5중 필터 시스템</h3>
            <ul>
                <li><strong>1차:</strong> 거시경제 (QQQ 120일선 + 금리 급등 체크)</li>
                <li><strong>2차:</strong> 뉴스 감성 (VADER 분석)</li>
                <li><strong>3차:</strong> 차트 기술 (RSI + 골든크로스)</li>
                <li><strong>4차:</strong> 옵션 데이터 (IV Rank ≤ 30% + Bullish Flow) ⭐ NEW</li>
                <li><strong>5차:</strong> 지지/저항선 (현재가가 지지선 대비 +3% 이내) ⭐ NEW</li>
            </ul>
        </div>
        
        <div class="status-grid">
            <div class="status-box" style="background-color: {market_color}; color: white;">
                시장 상태 (QQQ)<br>
                {market_status}<br>
                <small>${qqq_price:.2f} / 120일선: ${qqq_ma120:.2f}</small>
            </div>
            <div class="status-box" style="background-color: {'red' if tnx_spike else 'lightgreen'}; color: {'white' if tnx_spike else 'black'};">
                금리 상태 (^TNX)<br>
                {'🚨 급등 경보' if tnx_spike else '✅ 안정'}<br>
                <small>{tnx_price:.2f}% (전일 대비: {tnx_change:+.2f}%)</small>
            </div>
        </div>
        
        {crash_alert}
        
        <table>
            <thead>
                <tr>
                    <th>그룹</th>
                    <th>종목명</th>
                    <th>현재가</th>
                    <th>RSI</th>
                    <th>기준 (매수/매도)</th>
                    <th>뉴스 감성</th>
                    <th>IV Rank ⭐</th>
                    <th>Options Flow ⭐</th>
                    <th>P/C Ratio ⭐</th>
                    <th>가장 가까운 지지선 ⭐</th>
                    <th>신호</th>
                </tr>
            </thead>
            <tbody>
                {html_rows}
            </tbody>
        </table>
        
        <div class="checklist-box">
            <div class="checklist-title">✅ [운영 원칙 체크리스트]</div>
            <ul style="margin: 0; padding-left: 20px;">
                <li><strong>자금 배분:</strong> 주식 70% : 현금 30% 비중을 항상 유지하세요.</li>
                <li><strong>손절 규칙:</strong> 개별 종목 -10% 손실 시 절반 매도, -15% 손실 시 전량 매도하세요.</li>
                <li><strong>분할 매수:</strong> 한 번에 사지 말고, 3번에 나누어 진입하세요.</li>
                <li><strong>뉴스 확인:</strong> 악재(🔴) 종목은 감성 점수가 회복될 때까지 대기하세요.</li>
                <li><strong>옵션 확인:</strong> IV Rank가 30% 이하이고 Bullish Flow가 감지될 때만 진입하세요.</li>
                <li><strong>지지선 확인:</strong> 현재가가 가장 가까운 지지선 대비 +3% 이내일 때 최적 진입 타이밍입니다.</li>
            </ul>
        </div>
    </div>
</body>
</html>
"""

with open(output_html, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"✅ 리포트 생성 완료: {output_html}")
webbrowser.open(output_html)
print("🌐 브라우저에서 리포트를 열었습니다.")

print(f"\n{'='*70}")
print("✅ Ultimate M7 Bot (5중 필터) 실행 완료!")
print(f"{'='*70}")
