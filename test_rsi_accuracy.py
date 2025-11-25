"""
RSI 계산 정확성 검증 스크립트
Wilder's EMA vs Simple MA vs External Sources
"""

import yfinance as yf
import pandas as pd
import numpy as np

def calculate_rsi_wilder(df, period=14):
    """
    Wilder's Smoothed RSI (정확한 방식)
    """
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_rsi_simple(df, period=14):
    """
    Simple Moving Average RSI (부정확한 방식)
    """
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compare_rsi_methods(ticker='XLK'):
    print(f"\n{'='*60}")
    print(f"RSI 계산 비교 분석: {ticker}")
    print(f"{'='*60}\n")
    
    # 데이터 가져오기
    df = yf.download(ticker, period='3mo', progress=False)
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    if df.empty:
        print("❌ 데이터를 가져올 수 없습니다.")
        return
    
    # 두 가지 방법으로 RSI 계산
    rsi_wilder = calculate_rsi_wilder(df)
    rsi_simple = calculate_rsi_simple(df)
    
    # 최근 값 비교
    current_wilder = rsi_wilder.iloc[-1]
    current_simple = rsi_simple.iloc[-1]
    
    print(f"📊 최근 RSI 값 ({df.index[-1].strftime('%Y-%m-%d')})")
    print(f"   • Wilder's EMA: {current_wilder:.2f}")
    print(f"   • Simple MA:    {current_simple:.2f}")
    print(f"   • 차이:          {abs(current_wilder - current_simple):.2f}")
    
    # 과거 10일 비교
    print(f"\n📈 최근 10일 비교:")
    print(f"{'Date':<12} {'Wilder RSI':<12} {'Simple RSI':<12} {'차이':<8}")
    print("-" * 50)
    
    for i in range(-10, 0):
        date = df.index[i].strftime('%Y-%m-%d')
        w_rsi = rsi_wilder.iloc[i]
        s_rsi = rsi_simple.iloc[i]
        diff = abs(w_rsi - s_rsi)
        print(f"{date:<12} {w_rsi:>10.2f}  {s_rsi:>10.2f}  {diff:>6.2f}")
    
    # 통계
    avg_diff = abs(rsi_wilder - rsi_simple).mean()
    max_diff = abs(rsi_wilder - rsi_simple).max()
    
    print(f"\n📊 통계:")
    print(f"   • 평균 차이: {avg_diff:.2f}")
    print(f"   • 최대 차이: {max_diff:.2f}")
    
    # 판정
    print(f"\n{'='*60}")
    if avg_diff > 5:
        print("⚠️  경고: 두 방법의 차이가 큽니다!")
        print("   → Wilder's EMA 방식을 사용해야 합니다.")
    else:
        print("✅ 두 방법의 차이가 작습니다.")
    
    # 외부 소스와 비교 (TradingView 예상 범위)
    print(f"\n📡 외부 검증 (예상 범위):")
    print(f"   • TradingView 예상: 50-58")
    print(f"   • 대시보드 표시:     36.5")
    print(f"   • Wilder's 계산:    {current_wilder:.2f}")
    
    if 50 <= current_wilder <= 58:
        print("   ✅ Wilder's 방식이 정확합니다!")
    else:
        print("   ⚠️  추가 검증이 필요합니다.")
    
    print(f"{'='*60}\n")
    
    return {
        'wilder': current_wilder,
        'simple': current_simple,
        'difference': abs(current_wilder - current_simple)
    }

def test_all_stocks():
    """
    모든 주요 종목에 대해 테스트
    """
    stocks = ['XLK', 'MSFT', 'GOOGL', 'META', 'NVDA']
    
    print("\n" + "="*60)
    print("전체 종목 RSI 검증")
    print("="*60)
    
    results = []
    for ticker in stocks:
        try:
            result = compare_rsi_methods(ticker)
            results.append({
                'ticker': ticker,
                'wilder_rsi': result['wilder'],
                'simple_rsi': result['simple'],
                'difference': result['difference']
            })
        except Exception as e:
            print(f"❌ {ticker} 오류: {e}")
    
    # 요약
    print("\n" + "="*60)
    print("요약")
    print("="*60)
    print(f"{'Ticker':<8} {'Wilder RSI':<12} {'Simple RSI':<12} {'차이':<8}")
    print("-" * 50)
    
    for r in results:
        print(f"{r['ticker']:<8} {r['wilder_rsi']:>10.2f}  {r['simple_rsi']:>10.2f}  {r['difference']:>6.2f}")
    
    avg_diff = sum(r['difference'] for r in results) / len(results)
    print(f"\n평균 차이: {avg_diff:.2f}")
    
    if avg_diff > 5:
        print("\n⚠️  결론: Simple MA 방식은 부정확합니다!")
        print("   → Wilder's EMA 방식으로 변경해야 합니다.")
    else:
        print("\n✅ 두 방식의 차이가 작습니다.")

if __name__ == "__main__":
    # 개별 테스트
    compare_rsi_methods('XLK')
    
    # 전체 테스트
    test_all_stocks()
