import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
import webbrowser

# --- Configuration ---
# Set paths
script_dir = os.path.dirname(os.path.abspath(__file__))
output_html = os.path.join(script_dir, 'daily_report.html')
output_chart = os.path.join(script_dir, 'bot_chart.png')

# Korean Font Setting
font_path = "C:/Windows/Fonts/malgun.ttf"
font_name = fm.FontProperties(fname=font_path).get_name()
plt.rc('font', family=font_name)
plt.rc('axes', unicode_minus=False)

# --- Data Fetching ---
print("데이터 수집 중 (TSLA, QQQ)...")
tickers = ['TSLA', 'QQQ']
data = yf.download(tickers, period='1y', auto_adjust=False)

# Separate DataFrames
tsla = data['Close']['TSLA'].to_frame()
tsla.columns = ['Close']
qqq = data['Close']['QQQ'].to_frame()
qqq.columns = ['Close']

# --- Indicator Calculation ---
# 1. QQQ MA120 (Market Filter)
qqq['MA120'] = qqq['Close'].rolling(window=120).mean()

# 2. TSLA Indicators
tsla['MA20'] = tsla['Close'].rolling(window=20).mean()
tsla['MA60'] = tsla['Close'].rolling(window=60).mean()

# RSI (14-day)
delta = tsla['Close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
tsla['RSI'] = 100 - (100 / (1 + rs))

# --- Logic & Signal Determination ---
# Get latest values
latest_date = tsla.index[-1]
tsla_price = tsla['Close'].iloc[-1]
tsla_rsi = tsla['RSI'].iloc[-1]
tsla_ma20 = tsla['MA20'].iloc[-1]
tsla_ma60 = tsla['MA60'].iloc[-1]

qqq_price = qqq['Close'].iloc[-1]
qqq_ma120 = qqq['MA120'].iloc[-1]

# Conditions
is_market_safe = qqq_price > qqq_ma120
is_rsi_oversold = tsla_rsi < 30
is_rsi_overbought = tsla_rsi > 70
is_golden_cross = tsla_ma20 > tsla_ma60

# Determine Action
action = "관망 (Hold)"
color = "#f1c40f" # Yellow
status_msg = "특이 사항 없음"

if not is_market_safe:
    action = "매수 금지 (Market Risk)"
    color = "#e74c3c" # Red
    status_msg = "시장 위험: QQQ가 120일선 아래에 있음"
elif is_rsi_overbought:
    action = "이익 실현 (Sell)"
    color = "#e74c3c" # Red
    status_msg = "RSI 과열 (70 초과)"
elif is_market_safe and is_rsi_oversold and is_golden_cross:
    action = "강력 매수 (Strong Buy)"
    color = "#2ecc71" # Green
    status_msg = "시장 안전 + RSI 침체 + 골든크로스"
elif is_market_safe and is_rsi_oversold:
    action = "매수 관찰 (Watch)"
    color = "#f39c12" # Orange
    status_msg = "RSI 침체이나 골든크로스 미확정"

# --- Chart Generation ---
plt.figure(figsize=(10, 8))

# Subplot 1: Price & MAs
plt.subplot(2, 1, 1)
plt.plot(tsla.index, tsla['Close'], label='TSLA Price', color='black')
plt.plot(tsla.index, tsla['MA20'], label='MA20', color='blue', alpha=0.7)
plt.plot(tsla.index, tsla['MA60'], label='MA60', color='orange', alpha=0.7)
plt.title(f'테슬라(TSLA) 주가 및 이동평균선 ({latest_date.strftime("%Y-%m-%d")})', fontsize=14)
plt.legend()
plt.grid(True, alpha=0.3)

# Subplot 2: RSI
plt.subplot(2, 1, 2)
plt.plot(tsla.index, tsla['RSI'], label='RSI(14)', color='purple')
plt.axhline(70, color='red', linestyle='--', alpha=0.5)
plt.axhline(30, color='green', linestyle='--', alpha=0.5)
plt.fill_between(tsla.index, 70, tsla['RSI'], where=(tsla['RSI'] >= 70), color='red', alpha=0.3)
plt.fill_between(tsla.index, 30, tsla['RSI'], where=(tsla['RSI'] <= 30), color='green', alpha=0.3)
plt.title('RSI (상대강도지수)', fontsize=14)
plt.legend()
plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(output_chart)
plt.close()

# --- HTML Report Generation ---
html_content = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>오늘의 테슬라(TSLA) 리포트</title>
    <style>
        body {{ font-family: 'Malgun Gothic', sans-serif; margin: 0; padding: 20px; background-color: #f0f2f5; }}
        .container {{ max-width: 800px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
        h1 {{ text-align: center; color: #333; margin-bottom: 10px; }}
        .date {{ text-align: center; color: #666; margin-bottom: 30px; font-size: 1.1em; }}
        
        .signal-box {{ 
            background-color: {color}; 
            color: white; 
            padding: 30px; 
            text-align: center; 
            border-radius: 10px; 
            margin-bottom: 30px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.2);
        }}
        .signal-title {{ font-size: 1.5em; margin-bottom: 10px; opacity: 0.9; }}
        .signal-action {{ font-size: 3em; font-weight: bold; }}
        .signal-desc {{ font-size: 1.2em; margin-top: 10px; }}

        .summary-table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }}
        .summary-table th, .summary-table td {{ padding: 15px; border-bottom: 1px solid #eee; text-align: center; }}
        .summary-table th {{ background-color: #f8f9fa; color: #555; }}
        
        .chart-container {{ text-align: center; margin-bottom: 30px; }}
        img {{ max-width: 100%; border-radius: 10px; border: 1px solid #eee; }}

        .warning-box {{ 
            border: 2px solid #e74c3c; 
            background-color: #fdecea; 
            color: #c0392b; 
            padding: 15px; 
            text-align: center; 
            border-radius: 8px; 
            font-weight: bold;
            font-size: 1.1em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 오늘의 테슬라(TSLA) AI 리포트</h1>
        <div class="date">{latest_date.strftime('%Y년 %m월 %d일')} 기준</div>

        <div class="signal-box">
            <div class="signal-title">오늘의 행동</div>
            <div class="signal-action">{action}</div>
            <div class="signal-desc">{status_msg}</div>
        </div>

        <table class="summary-table">
            <thead>
                <tr>
                    <th>지표</th>
                    <th>값</th>
                    <th>상태</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>TSLA 현재가</td>
                    <td>${tsla_price:.2f}</td>
                    <td>-</td>
                </tr>
                <tr>
                    <td>TSLA RSI(14)</td>
                    <td>{tsla_rsi:.2f}</td>
                    <td>{'과열 (>70)' if tsla_rsi > 70 else '침체 (<30)' if tsla_rsi < 30 else '중립'}</td>
                </tr>
                <tr>
                    <td>TSLA 추세 (MA20 vs MA60)</td>
                    <td>{'골든크로스 (상승)' if is_golden_cross else '데드크로스 (하락)'}</td>
                    <td>MA20: ${tsla_ma20:.2f}</td>
                </tr>
                <tr>
                    <td>QQQ 시장 필터 (120일선)</td>
                    <td>{'안전 (Safe)' if is_market_safe else '위험 (Risk)'}</td>
                    <td>현재: ${qqq_price:.2f} / 120일선: ${qqq_ma120:.2f}</td>
                </tr>
            </tbody>
        </table>

        <div class="chart-container">
            <img src="bot_chart.png" alt="테슬라 차트">
        </div>

        <div class="warning-box">
            ⚠️ 손절 원칙: 진입가 대비 -7% 하락 시 무조건 손절하세요!
        </div>
    </div>
</body>
</html>
"""

with open(output_html, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"리포트 생성 완료: {output_html}")

# Open in browser
webbrowser.open(output_html)
print("브라우저에서 리포트를 열었습니다.")
