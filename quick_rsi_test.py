import yfinance as yf
import pandas as pd

# Test current RSI calculation
ticker = "XLK"
print(f"Testing {ticker} RSI calculation...")

df = yf.download(ticker, period="2y", progress=False)
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

delta = df['Close'].diff()

# Wilder's EMA (Correct)
gain_ema = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
loss_ema = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
rsi_ema = 100 - (100 / (1 + (gain_ema / loss_ema)))

# Simple MA (Incorrect)
gain_ma = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss_ma = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rsi_ma = 100 - (100 / (1 + (gain_ma / loss_ma)))

print(f"\n{'='*50}")
print(f"XLK RSI Comparison")
print(f"{'='*50}")
print(f"Wilder's EMA (Correct):  {rsi_ema.iloc[-1]:.2f}")
print(f"Simple MA (Incorrect):   {rsi_ma.iloc[-1]:.2f}")
print(f"{'='*50}")
print(f"\nIf Dashboard shows ~{rsi_ma.iloc[-1]:.1f}, it's using Simple MA")
print(f"If Dashboard shows ~{rsi_ema.iloc[-1]:.1f}, it's using Wilder's EMA")
