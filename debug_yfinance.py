import yfinance as yf
import pandas as pd

def debug_yfinance():
    ticker = "AAPL"
    print(f"Downloading data for {ticker}...")
    df = yf.download(ticker, period="6mo", progress=False)
    
    print("\n--- DataFrame Shape ---")
    print(df.shape)
    
    print("\n--- DataFrame Columns ---")
    print(df.columns)
    
    print("\n--- DataFrame Head ---")
    print(df.head())
    
    print("\n--- Checking 'Close' column type ---")
    try:
        close_col = df['Close']
        print(type(close_col))
        print(close_col.head())
    except Exception as e:
        print(f"Error accessing 'Close': {e}")

    # Check if columns are MultiIndex
    if isinstance(df.columns, pd.MultiIndex):
        print("\n⚠️ Columns are MultiIndex!")
        # Try flattening
        df.columns = df.columns.droplevel(1)
        print("Flattened columns:", df.columns)
        print(df.head())

if __name__ == "__main__":
    debug_yfinance()
