import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

ticker = "NVDA"
print("="*70)
print(f"NVDA RSI Analysis - Comparing Data Periods")
print("="*70)

# Get data for last 50 days (minimal for RSI calculation)
end_date = datetime.now()
start_date = end_date - timedelta(days=50)

df = yf.download(ticker, start=start_date, end=end_date, progress=False)
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

print(f"\nData from {df.index[0].date()} to {df.index[-1].date()}")
print(f"Total days: {len(df)}")
print(f"Latest close: ${df['Close'].iloc[-1]:.2f}\n")

# Calculate RSI with Wilder's method
delta = df['Close'].diff()
gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
rsi_wilder = 100 - (100 / (1 + (gain / loss)))

# Calculate RSI with SMA method  
gain_sma = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss_sma = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rsi_sma = 100 - (100 / (1 + (gain_sma / loss_sma)))

print("Last 5 days RSI comparison:")
print("-" * 70)
print(f"{'Date':<12} {'Close':>10} {'Wilder RSI':>12} {'SMA RSI':>12}")
print("-" * 70)

for i in range(-5, 0):
    date = df.index[i].strftime('%Y-%m-%d')
    close = df['Close'].iloc[i]
    rsi_w = rsi_wilder.iloc[i]
    rsi_s = rsi_sma.iloc[i]
    print(f"{date:<12} ${close:>9.2f} {rsi_w:>12.2f} {rsi_s:>12.2f}")

print("-" * 70)
print(f"\nKorean App shows: 55.53")
print(f"Our Wilder's RSI:  {rsi_wilder.iloc[-1]:.2f}")
print(f"Our SMA RSI:       {rsi_sma.iloc[-1]:.2f}")
print(f"\nDifference: {abs(rsi_wilder.iloc[-1] - 55.53):.2f} points")

# Check if Korean app might be using intraday data
print("\n" + "="*70)
print("Possible causes of discrepancy:")
print("="*70)
print("1. Data timing: Korean app uses real-time, yfinance has delay")
print("2. Data source: Different price data (exchange vs aggregated)")
print("3. Calculation: Korean app might use different RSI variant")
print("4. Period: App might use intraday (1hr, 4hr) instead of daily")
print("="*70)
