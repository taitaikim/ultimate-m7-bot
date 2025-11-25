import yfinance as yf
import pandas as pd
from datetime import datetime

def calculate_rsi_wilder(df, period=14):
    """Wilder's RSI calculation"""
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_rsi_cutler(df, period=14):
    """Cutler's RSI (Simple Moving Average)"""
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

print("="*70)
print("NVDA RSI 상세 비교 분석")
print("="*70)

# Test multiple data periods
for period in ["1mo", "3mo", "6mo", "1y", "2y"]:
    print(f"\n【 Data Period: {period} 】")
    
    df = yf.download("NVDA", period=period, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    if df.empty:
        print("  No data available")
        continue
    
    # Calculate both methods
    rsi_wilder = calculate_rsi_wilder(df)
    rsi_cutler = calculate_rsi_cutler(df)
    
    # Get last values
    last_wilder = rsi_wilder.iloc[-1]
    last_cutler = rsi_cutler.iloc[-1]
    last_close = df['Close'].iloc[-1]
    last_date = df.index[-1]
    
    print(f"  Last Close: ${last_close:.2f}")
    print(f"  Last Date:  {last_date.strftime('%Y-%m-%d')}")
    print(f"  Wilder RSI: {last_wilder:.2f}")
    print(f"  Cutler RSI: {last_cutler:.2f}")
    
    # Compare with expected value
    expected = 55.53
    wilder_diff = abs(last_wilder - expected)
    cutler_diff = abs(last_cutler - expected)
    
    if wilder_diff < 1.0:
        print(f"  ✅ Wilder's matches! (차이: {wilder_diff:.2f})")
    elif cutler_diff < 1.0:
        print(f"  ✅ Cutler's matches! (차이: {cutler_diff:.2f})")
    else:
        print(f"  ❌ Neither matches (Wilder 차이: {wilder_diff:.2f}, Cutler 차이: {cutler_diff:.2f})")

print("\n" + "="*70)
print("현재 시각:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
print("="*70)
