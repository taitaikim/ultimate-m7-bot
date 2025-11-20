import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# 한글 폰트 설정 (Windows)
plt.rc('font', family='Malgun Gothic')
plt.rc('axes', unicode_minus=False)

# Set paths
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(script_dir, 'stock_data.csv')
output_file = os.path.join(script_dir, 'tsla_analysis.png')

# Read the data
df = pd.read_csv(csv_path)

# Convert Date to datetime
df['Date'] = pd.to_datetime(df['Date'])

# Filter for TSLA
tsla = df[df['Ticker'] == 'TSLA'].copy()
tsla.sort_values('Date', inplace=True)

# Calculate Moving Averages
tsla['MA20'] = tsla['Close'].rolling(window=20).mean()
tsla['MA60'] = tsla['Close'].rolling(window=60).mean()

# Calculate RSI (14-day)
delta = tsla['Close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
tsla['RSI'] = 100 - (100 / (1 + rs))

# Identify Golden Cross
# MA20 crosses above MA60
tsla['GoldenCross'] = (tsla['MA20'] > tsla['MA60']) & (tsla['MA20'].shift(1) < tsla['MA60'].shift(1))

# Set the style
sns.set_theme(style="darkgrid", rc={"font.family": "Malgun Gothic", "axes.unicode_minus": False})

# Create the plot with subplots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [2, 1]})

# Plot 1: Price & Moving Averages
ax1.plot(tsla['Date'], tsla['Close'], label='종가 (Close Price)', color='black', alpha=0.5)
ax1.plot(tsla['Date'], tsla['MA20'], label='20일 이동평균선', color='blue', linestyle='--')
ax1.plot(tsla['Date'], tsla['MA60'], label='60일 이동평균선', color='red', linestyle='--')

# Plot Golden Cross
golden_crosses = tsla[tsla['GoldenCross']]
ax1.scatter(golden_crosses['Date'], golden_crosses['MA20'], color='gold', marker='*', s=200, label='골든크로스 (Golden Cross)', zorder=5)

ax1.set_title('테슬라(TSLA) 주가 분석: 이동평균선 & 골든크로스', fontsize=16)
ax1.set_ylabel('주가', fontsize=12)
ax1.legend(loc='upper left')

# Plot 2: RSI
ax2.plot(tsla['Date'], tsla['RSI'], label='RSI (14일)', color='purple')
ax2.axhline(70, color='red', linestyle='--', alpha=0.5, label='과매수 (70)')
ax2.axhline(30, color='green', linestyle='--', alpha=0.5, label='과매도 (30)')
ax2.fill_between(tsla['Date'], 70, 30, color='gray', alpha=0.1)

ax2.set_title('상대강도지수 (RSI)', fontsize=14)
ax2.set_xlabel('날짜', fontsize=12)
ax2.set_ylabel('RSI', fontsize=12)
ax2.legend(loc='upper left')

# Adjust layout
plt.tight_layout()

# Save the plot
plt.savefig(output_file)
plt.close()

print(f"테슬라 분석 차트를 {output_file} 파일로 저장했습니다.")
print(f"총 {len(golden_crosses)}개의 골든크로스 지점을 발견했습니다.")
if not golden_crosses.empty:
    print("골든크로스 발생 날짜:")
    print(golden_crosses['Date'].dt.strftime('%Y-%m-%d').to_string(index=False))
