import yfinance as yf
import pandas as pd

ticker = "NVDA"
print(f"Testing {ticker} with different periods...\n")

for period in ["1mo", "3mo", "6mo", "1y", "2y"]:
    df = yf.download(ticker, period=period, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    if df.empty:
        continue
    
    # Wilder's EMA
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rsi = 100 - (100 / (1 + (gain / loss)))
    
    print(f"Period: {period:4s} | RSI: {rsi.iloc[-1]:6.2f} | Close: ${df['Close'].iloc[-1]:7.2f} | Date: {df.index[-1].date()}")

print(f"\nExpected from Korean app: 55.53")
print(f"Checking which period matches...")
