import yfinance as yf
import pandas as pd

ticker = "NVDA"
print(f"Downloading data for {ticker}...")
df = yf.download(ticker, period="1y", interval="1d", progress=False)

print("\nColumns before processing:")
print(df.columns)

if isinstance(df.columns, pd.MultiIndex):
    print("\nDetected MultiIndex")
    print("Levels:", df.columns.nlevels)
    print("Level 0:", df.columns.get_level_values(0))
    print("Level 1:", df.columns.get_level_values(1) if df.columns.nlevels > 1 else "N/A")
    
    # Try the existing logic
    df_dropped = df.copy()
    df_dropped.columns = df_dropped.columns.droplevel(0)
    print("\nColumns after droplevel(0):")
    print(df_dropped.columns)
else:
    print("\nNot a MultiIndex")

print("\nHead:")
print(df.head())
