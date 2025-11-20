import pandas as pd
import os

# Set paths
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(script_dir, 'stock_data.csv')

# Read the data
df = pd.read_csv(csv_path)

# Convert Date to datetime
df['Date'] = pd.to_datetime(df['Date'])

# Filter for TSLA
tsla = df[df['Ticker'] == 'TSLA'].copy()
tsla.sort_values('Date', inplace=True)
tsla.reset_index(drop=True, inplace=True)

# Calculate Moving Averages
tsla['MA20'] = tsla['Close'].rolling(window=20).mean()
tsla['MA60'] = tsla['Close'].rolling(window=60).mean()

# Calculate RSI (14-day)
delta = tsla['Close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
tsla['RSI'] = 100 - (100 / (1 + rs))

# Identify Signals
# Buy: Golden Cross AND RSI < 70
tsla['GoldenCross'] = (tsla['MA20'] > tsla['MA60']) & (tsla['MA20'].shift(1) < tsla['MA60'].shift(1))
tsla['Buy_Signal'] = tsla['GoldenCross'] & (tsla['RSI'] < 70)

# Sell: Dead Cross OR RSI > 80 (Overbought)
tsla['DeadCross'] = (tsla['MA20'] < tsla['MA60']) & (tsla['MA20'].shift(1) > tsla['MA60'].shift(1))
tsla['Sell_Signal'] = tsla['DeadCross'] | (tsla['RSI'] > 80)

# Function to calculate Stochastic Oscillator
def calculate_stochastic(df, n=14, m=3, t=3):
    low_min = df['Low'].rolling(window=n).min()
    high_max = df['High'].rolling(window=n).max()
    
    fast_k = ((df['Close'] - low_min) / (high_max - low_min)) * 100
    slow_k = fast_k.rolling(window=m).mean()
    slow_d = slow_k.rolling(window=t).mean()
    
    return slow_k, slow_d

# 1. Calculate Daily Stochastic
tsla['Daily_K'], tsla['Daily_D'] = calculate_stochastic(tsla)

# Set Date as index for resampling and merging
tsla.set_index('Date', inplace=True)

# 2. Calculate Weekly Stochastic (Resampling)
tsla_weekly = tsla.resample('W-FRI').agg({
    'Open': 'first',
    'High': 'max',
    'Low': 'min',
    'Close': 'last',
    'Volume': 'sum'
})
tsla_weekly['Weekly_K'], tsla_weekly['Weekly_D'] = calculate_stochastic(tsla_weekly)

# Calculate Signals on Weekly Data
# Buy: K < 20 AND Golden Cross (K > D)
# Sell: K > 80 AND Dead Cross (K < D)
tsla_weekly['Prev_K'] = tsla_weekly['Weekly_K'].shift(1)
tsla_weekly['Prev_D'] = tsla_weekly['Weekly_D'].shift(1)

tsla_weekly['Stoch_Buy'] = (tsla_weekly['Weekly_K'] < 20) & \
                           (tsla_weekly['Weekly_K'] > tsla_weekly['Weekly_D']) & \
                           (tsla_weekly['Prev_K'] < tsla_weekly['Prev_D'])

tsla_weekly['Stoch_Sell'] = (tsla_weekly['Weekly_K'] > 80) & \
                            (tsla_weekly['Weekly_K'] < tsla_weekly['Weekly_D']) & \
                            (tsla_weekly['Prev_K'] > tsla_weekly['Prev_D'])

# Merge Weekly Signals to Daily (Forward Fill)
# This ensures that if a signal happens on Friday, it is available for trading the next week
tsla['Stoch_Buy'] = tsla_weekly['Stoch_Buy'].reindex(tsla.index, method='ffill')
tsla['Stoch_Sell'] = tsla_weekly['Stoch_Sell'].reindex(tsla.index, method='ffill')

# Reset index to make Date a column again for iteration
tsla.reset_index(inplace=True)

import yfinance as yf

# Fetch VIX Data
print("VIX 공포 지수 데이터 가져오는 중...")
start_date_vix = tsla['Date'].iloc[0]
end_date_vix = tsla['Date'].iloc[-1]
vix = yf.download('^VIX', start=start_date_vix, end=end_date_vix, auto_adjust=False)

# Prepare VIX data for merging
vix = vix[['Close']].copy()
vix.columns = ['VIX']
vix.reset_index(inplace=True)
vix['Date'] = pd.to_datetime(vix['Date'])

# Merge VIX to TSLA data
tsla = pd.merge(tsla, vix, on='Date', how='left')
tsla['VIX'] = tsla['VIX'].fillna(method='ffill') # Fill missing VIX data

# --- Strategy 1: RSI (Existing) ---
initial_capital = 10000
capital = initial_capital
shares = 0
trades = 0
trade_log_rsi = []

print(f"전략 1: RSI 전략 백테스팅 시작...")
for i, row in tsla.iterrows():
    if row['Buy_Signal']:
        if shares == 0:
            shares = capital / row['Close']
            capital = 0
            trades += 1
            trade_log_rsi.append({'날짜': row['Date'], '유형': '매수', '가격': row['Close'], '수량': shares, '자본금': 0, '비고': 'RSI 전략'})
    elif row['Sell_Signal']:
        if shares > 0:
            capital = shares * row['Close']
            shares = 0
            trades += 1
            trade_log_rsi.append({'날짜': row['Date'], '유형': '매도', '가격': row['Close'], '수량': 0, '자본금': capital, '비고': 'RSI 전략'})

final_price = tsla.iloc[-1]['Close']
rsi_final_capital = (shares * final_price) if shares > 0 else capital
rsi_return = (rsi_final_capital - initial_capital) / initial_capital * 100

# --- Strategy 2: Weekly Stochastic Swing ---
capital = initial_capital
shares = 0
trades_stoch = 0
trade_log_stoch = []

print(f"전략 2: 주봉 스토캐스틱 스윙 전략 백테스팅 시작...")
for i, row in tsla.iterrows():
    if row['Stoch_Buy']:
        if shares == 0:
            shares = capital / row['Close']
            capital = 0
            trades_stoch += 1
            trade_log_stoch.append({'날짜': row['Date'], '유형': '매수', '가격': row['Close'], '수량': shares, '자본금': 0, '비고': '스토캐스틱 스윙'})
    elif row['Stoch_Sell']:
        if shares > 0:
            capital = shares * row['Close']
            shares = 0
            trades_stoch += 1
            trade_log_stoch.append({'날짜': row['Date'], '유형': '매도', '가격': row['Close'], '수량': 0, '자본금': capital, '비고': '스토캐스틱 스윙'})

stoch_final_capital = (shares * final_price) if shares > 0 else capital
stoch_return = (stoch_final_capital - initial_capital) / initial_capital * 100

# --- Strategy 3: VIX Fear Hunter ---
capital = initial_capital
shares = 0
trades_vix = 0
trade_log_vix = []

print(f"전략 3: VIX 공포 매수 (Fear Hunter) 전략 백테스팅 시작...")
for i, row in tsla.iterrows():
    # Skip if VIX is NaN
    if pd.isna(row['VIX']):
        continue

    # Buy Condition: (VIX >= 20 OR RSI < 30) AND (Close < MA20)
    # Panic Buy: High Fear or Oversold, and Price is depressed
    buy_condition = ((row['VIX'] >= 20) | (row['RSI'] < 30)) & (row['Close'] < row['MA20'])
    
    # Sell Condition: RSI > 75
    # Greed Sell: Overbought
    sell_condition = row['RSI'] > 75

    if buy_condition:
        if shares == 0:
            shares = capital / row['Close']
            capital = 0
            trades_vix += 1
            trade_log_vix.append({'날짜': row['Date'], '유형': '매수', '가격': row['Close'], '수량': shares, '자본금': 0, '비고': f"VIX: {row['VIX']:.2f}"})

    elif sell_condition:
        if shares > 0:
            capital = shares * row['Close']
            shares = 0
            trades_vix += 1
            trade_log_vix.append({'날짜': row['Date'], '유형': '매도', '가격': row['Close'], '수량': 0, '자본금': capital, '비고': f"RSI: {row['RSI']:.2f}"})

vix_final_capital = (shares * final_price) if shares > 0 else capital
vix_return = (vix_final_capital - initial_capital) / initial_capital * 100

# --- Buy & Hold ---
initial_price = tsla.iloc[0]['Close']
buy_and_hold_return = (final_price - initial_price) / initial_price * 100

# --- Comparison & Reporting ---
print("-" * 50)
print(f"1. 단순 보유 수익률: {buy_and_hold_return:.2f}%")
print(f"2. RSI 전략 수익률: {rsi_return:.2f}% (매매 {trades}회)")
print(f"3. 스토캐스틱 스윙 수익률: {stoch_return:.2f}% (매매 {trades_stoch}회)")
print(f"4. VIX 공포 전략 수익률: {vix_return:.2f}% (매매 {trades_vix}회)")

# Determine Winner
strategies = {
    '단순 보유': buy_and_hold_return, 
    'RSI 전략': rsi_return, 
    '스토캐스틱 스윙': stoch_return,
    'VIX 공포 전략': vix_return
}
winner = max(strategies, key=strategies.get)
print(f"🏆 우승 전략: {winner} ({strategies[winner]:.2f}%)")

# Export to Excel
output_excel = os.path.join(script_dir, 'trade_result.xlsx')
trade_df_rsi = pd.DataFrame(trade_log_rsi)
trade_df_stoch = pd.DataFrame(trade_log_stoch)
trade_df_vix = pd.DataFrame(trade_log_vix)

summary_data = {
    '전략': ['단순 보유', 'RSI 전략', '스토캐스틱 스윙', 'VIX 공포 전략'],
    '수익률': [f"{buy_and_hold_return:.2f}%", f"{rsi_return:.2f}%", f"{stoch_return:.2f}%", f"{vix_return:.2f}%"],
    '최종 자본금': ['-', f"${rsi_final_capital:,.2f}", f"${stoch_final_capital:,.2f}", f"${vix_final_capital:,.2f}"],
    '매매 횟수': ['-', trades, trades_stoch, trades_vix]
}
summary_df = pd.DataFrame(summary_data)

try:
    with pd.ExcelWriter(output_excel) as writer:
        summary_df.to_excel(writer, sheet_name='요약', index=False)
        trade_df_rsi.to_excel(writer, sheet_name='RSI_매매내역', index=False)
        trade_df_stoch.to_excel(writer, sheet_name='스토캐스틱_매매내역', index=False)
        trade_df_vix.to_excel(writer, sheet_name='VIX_매매내역', index=False)
    print(f"백테스트 결과를 {output_excel} 파일로 저장했습니다.")
except Exception as e:
    print(f"엑셀 저장 오류: {e}")

# Generate Comparison Chart
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

font_path = "C:/Windows/Fonts/malgun.ttf"
font_name = fm.FontProperties(fname=font_path).get_name()
plt.rc('font', family=font_name)
plt.rc('axes', unicode_minus=False)

output_chart = os.path.join(script_dir, 'strategy_comparison.png')

plt.figure(figsize=(12, 6))
strat_names = ['단순 보유', 'RSI 전략', '스토캐스틱 스윙', 'VIX 공포 전략']
strat_returns = [buy_and_hold_return, rsi_return, stoch_return, vix_return]
colors = ['gray', 'blue', 'green', 'purple']

# Highlight winner
bar_colors = []
for r in strat_returns:
    if r == max(strat_returns):
        bar_colors.append('red') # Winner
    else:
        bar_colors.append('gray')

bars = plt.bar(strat_names, strat_returns, color=bar_colors)
plt.title('최종 4파전: 전략별 수익률 비교', fontsize=16)
plt.ylabel('수익률 (%)', fontsize=12)
plt.grid(axis='y', linestyle='--', alpha=0.7)

for bar in bars:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2.0, height, f'{height:.2f}%', ha='center', va='bottom', fontsize=12, fontweight='bold')

plt.tight_layout()
plt.savefig(output_chart)
plt.close()

# Export to HTML
output_html = os.path.join(script_dir, 'trade_result.html')

html_content = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>테슬라(TSLA) 전략 비교 리포트</title>
    <style>
        body {{ font-family: 'Malgun Gothic', sans-serif; margin: 20px; background-color: #f4f4f9; }}
        h1, h2 {{ color: #333; text-align: center; }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; background-color: white; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: center; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .summary-table th {{ background-color: #2196F3; }}
        .chart-container {{ text-align: center; margin: 30px 0; }}
        img {{ max-width: 100%; height: auto; border: 1px solid #ddd; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .winner-box {{ background-color: #fff3cd; border: 2px solid #ffc107; padding: 20px; text-align: center; border-radius: 10px; margin-bottom: 30px; }}
        .winner-title {{ font-size: 1.5em; font-weight: bold; color: #856404; }}
        .winner-text {{ font-size: 1.2em; margin-top: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 테슬라(TSLA) 최종 전략 비교 리포트</h1>
        
        <div class="winner-box">
            <div class="winner-title">🏆 우승 전략: {winner}</div>
            <div class="winner-text">수익률 <strong>{strategies[winner]:.2f}%</strong>로 가장 높은 성과를 기록했습니다!</div>
        </div>
        
        <h2>📊 전략 요약 (Summary)</h2>
        {summary_df.to_html(index=False, classes='summary-table', border=0)}
        
        <h2>📈 수익률 비교 차트</h2>
        <div class="chart-container">
            <img src="strategy_comparison.png" alt="수익률 비교 차트">
        </div>

        <h2>📝 RSI 전략 매매 내역</h2>
        {trade_df_rsi.to_html(index=False, border=0)}
        
        <h2>📝 스토캐스틱 스윙 전략 매매 내역</h2>
        {trade_df_stoch.to_html(index=False, border=0)}
        
        <h2>📝 VIX 공포 전략 매매 내역</h2>
        {trade_df_vix.to_html(index=False, border=0)}
        
        <p style="text-align: center; color: #666;">생성 시간: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</body>
</html>
"""

with open(output_html, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"HTML 리포트를 {output_html} 파일로 저장했습니다.")
