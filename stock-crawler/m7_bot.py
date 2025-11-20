import yfinance as yf
import pandas as pd
import os
import webbrowser
from datetime import datetime

# --- Configuration ---
script_dir = os.path.dirname(os.path.abspath(__file__))
output_html = os.path.join(script_dir, 'daily_report_m7.html')

# Stock Groups & Thresholds
GROUPS = {
    'A': {'stocks': ['NVDA', 'TSLA'], 'buy_rsi': 25, 'sell_rsi': 65, 'desc': '고변동성'},
    'B': {'stocks': ['META', 'AMZN', 'GOOGL'], 'buy_rsi': 30, 'sell_rsi': 70, 'desc': '중변동성'},
    'C': {'stocks': ['AAPL', 'MSFT'], 'buy_rsi': 35, 'sell_rsi': 75, 'desc': '저변동성'}
}

ALL_STOCKS = []
for g in GROUPS.values():
    ALL_STOCKS.extend(g['stocks'])
ALL_STOCKS.append('QQQ')

# --- Data Fetching ---
print("데이터 수집 중 (M7 + QQQ)...")
# Fetch enough data for MA120 and RSI calculation
# Use group_by='ticker' to have Tickers as top-level columns
data = yf.download(ALL_STOCKS, period='1y', auto_adjust=False, group_by='ticker')

if data.empty:
    print("데이터 다운로드 실패. 인터넷 연결을 확인하세요.")
    exit()

# --- Market Analysis (QQQ) ---
if 'QQQ' not in data.columns:
    print("QQQ 데이터를 찾을 수 없습니다.")
    exit()

qqq = data['QQQ'][['Close']].copy()
qqq['MA120'] = qqq['Close'].rolling(window=120).mean()
qqq_price = qqq['Close'].iloc[-1]
qqq_ma120 = qqq['MA120'].iloc[-1]
qqq_prev_close = qqq['Close'].iloc[-2]

# Filter 1: Trend (QQQ < 120MA)
is_market_uptrend = qqq_price > qqq_ma120

# Filter 2: Crash (Daily Drop < -3%)
daily_return = (qqq_price - qqq_prev_close) / qqq_prev_close * 100
is_market_crash = daily_return < -3.0

market_status = "안전 (Safe)"
market_color = "green"
if not is_market_uptrend:
    market_status = "위험 (Downtrend)"
    market_color = "red"
if is_market_crash:
    market_status = "🚨 급락 경보 (Crash Warning)"
    market_color = "darkred"

# --- Individual Stock Analysis ---
results = []

for group_name, group_info in GROUPS.items():
    buy_th = group_info['buy_rsi']
    sell_th = group_info['sell_rsi']
    
    for ticker in group_info['stocks']:
        if ticker not in data.columns:
            print(f"Warning: {ticker} data missing.")
            continue
            
        df = data[ticker][['Close']].copy()
        
        # Indicators
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
        
        # Signals
        signal = "관망 (Hold)"
        signal_color = "black"
        
        if not is_market_uptrend:
            signal = "매수 금지 (Market)"
            signal_color = "gray"
        elif is_market_crash:
             signal = "진입 주의 (Crash)"
             signal_color = "orange"
        else:
            if current_rsi < buy_th and is_golden_cross:
                signal = "매수 (BUY)"
                signal_color = "green"
            elif current_rsi > sell_th:
                signal = "매도 (SELL)"
                signal_color = "red"
        
        results.append({
            'group': group_name,
            'ticker': ticker,
            'price': current_price,
            'rsi': current_rsi,
            'threshold': f"{buy_th} / {sell_th}",
            'signal': signal,
            'signal_color': signal_color
        })

# --- HTML Generation ---
today_str = datetime.now().strftime('%Y년 %m월 %d일')

html_rows = ""
for r in results:
    html_rows += f"""
    <tr>
        <td class="group-{r['group']}">{r['group']}</td>
        <td style="font-weight:bold;">{r['ticker']}</td>
        <td>${r['price']:.2f}</td>
        <td style="color: {'red' if r['rsi'] > 70 else 'blue' if r['rsi'] < 30 else 'black'}">{r['rsi']:.2f}</td>
        <td>{r['threshold']}</td>
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
    <title>M7 봇 종합 상황판</title>
    <style>
        body {{ font-family: 'Malgun Gothic', sans-serif; margin: 0; padding: 20px; background-color: #f4f4f9; }}
        .container {{ max-width: 1000px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
        h1 {{ text-align: center; color: #333; }}
        .date {{ text-align: center; color: #666; margin-bottom: 20px; }}
        
        .market-box {{ text-align: center; padding: 15px; background-color: #eee; border-radius: 10px; margin-bottom: 20px; font-weight: bold; }}
        
        .alert-box {{ background-color: #ffebee; color: #c62828; padding: 15px; text-align: center; border: 2px solid #ef5350; border-radius: 10px; margin-bottom: 20px; font-weight: bold; animation: blink 2s infinite; }}
        
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }}
        th, td {{ padding: 12px; border-bottom: 1px solid #ddd; text-align: center; }}
        th {{ background-color: #f8f9fa; color: #333; }}
        
        .group-A {{ color: #e91e63; font-weight: bold; }}
        .group-B {{ color: #2196f3; font-weight: bold; }}
        .group-C {{ color: #4caf50; font-weight: bold; }}
        
        .checklist-box {{ border: 2px dashed #aaa; padding: 20px; border-radius: 10px; background-color: #fff9c4; }}
        .checklist-title {{ font-weight: bold; margin-bottom: 10px; font-size: 1.1em; }}
        
        @keyframes blink {{ 50% {{ opacity: 0.5; }} }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 M7 봇 종합 상황판</h1>
        <div class="date">{today_str} 기준</div>
        
        <div class="market-box" style="color: {market_color}">
            시장 상태 (QQQ): {market_status} <br>
            (현재가: ${qqq_price:.2f} / 120일선: ${qqq_ma120:.2f})
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
            </ul>
        </div>
    </div>
</body>
</html>
"""

with open(output_html, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"리포트 생성 완료: {output_html}")
webbrowser.open(output_html)
