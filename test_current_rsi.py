import yfinance as yf
import pandas as pd
import numpy as np

def test_rsi_logic():
    print(f"\n{'='*50}")
    print(f"RSI Calculation Diagnostic")
    print(f"{'='*50}")

    ticker = "XLK"
    print(f"Fetching data for {ticker} (Period: 2y)...")
    df = yf.download(ticker, period="2y", progress=False)
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if df.empty:
        print("❌ Failed to fetch data.")
        return

    print(f"Last 5 Close Prices:\n{df['Close'].tail(5)}")

    delta = df['Close'].diff()

    # 1. Wilder's EMA (Correct)
    # Note: standard Wilder's uses SMA for the first 14 periods, then EMA.
    # Pure EMA with adjust=False starts from the first value.
    # To match TradingView, we need enough history.
    gain_ema = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss_ema = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs_ema = gain_ema / loss_ema
    rsi_ema = 100 - (100 / (1 + rs_ema))
    
    # 2. Simple MA (Incorrect)
    gain_ma = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss_ma = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs_ma = gain_ma / loss_ma
    rsi_ma = 100 - (100 / (1 + rs_ma))

    last_date = df.index[-1].strftime('%Y-%m-%d')
    print(f"\nDate: {last_date}")
    print(f"Wilder's EMA RSI (2y Data): {rsi_ema.iloc[-1]:.2f}")
    print(f"Simple MA RSI (2y Data): {rsi_ma.iloc[-1]:.2f}")
    
    print(f"\nIf Dashboard shows ~{rsi_ma.iloc[-1]:.2f}, it is using Simple MA.")
    print(f"If Dashboard shows ~{rsi_ema.iloc[-1]:.2f}, it is using Wilder's EMA.")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    test_rsi_logic()
