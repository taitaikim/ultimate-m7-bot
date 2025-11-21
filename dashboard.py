"""
M7 Bot - Streamlit Dashboard (V4.1 Trendline + ATR)
Trendline Breakdown Strategy with ATR Position Sizing
"""

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta
from m7_core.strategy_v4 import TrendlineStrategy, RiskManager # 방금 만든 모듈 임포트

# 페이지 설정
st.set_page_config(page_title="M7 Bot V4.1 Dashboard", layout="wide")

st.title("🚀 M7 Bot V4.1: Trendline + ATR System")
st.markdown("---")

# --- 1. 사이드바 설정 (사용자 입력) ---
st.sidebar.header("⚙️ Trading Config")
ticker = st.sidebar.selectbox("Select Ticker", ["NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "GOOGL", "TQQQ"])
account_balance = st.sidebar.number_input("Account Balance ($)", value=10000, step=1000)
risk_pct = st.sidebar.slider("Risk per Trade (%)", 0.5, 5.0, 2.0)
atr_multiplier = st.sidebar.slider("Stop Loss (ATR Multiplier)", 1.0, 4.0, 2.0)

if st.sidebar.button("Analyze Strategy"):
    # --- 2. 데이터 로드 ---
    with st.spinner(f"Fetching data for {ticker}..."):
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        
        # MultiIndex Handling (Fix)
        if isinstance(df.columns, pd.MultiIndex):
            if 'Close' in df.columns.get_level_values(0):
                df.columns = df.columns.droplevel(1)
            elif df.columns.nlevels > 1 and 'Close' in df.columns.get_level_values(1):
                df.columns = df.columns.droplevel(0)
        
        # ATR 계산 (14일)
        df['High_Low'] = df['High'] - df['Low']
        df['High_Close'] = np.abs(df['High'] - df['Close'].shift())
        df['Low_Close'] = np.abs(df['Low'] - df['Close'].shift())
        df['TR'] = df[['High_Low', 'High_Close', 'Low_Close']].max(axis=1)
        df['ATR'] = df['TR'].rolling(window=14).mean()

    # --- 3. 전략 분석 실행 ---
    strategy = TrendlineStrategy(df)
    slope, intercept = strategy.calculate_resistance_line()
    is_breakout, trendline_price = strategy.check_breakout()
    
    current_price = df['Close'].iloc[-1]
    current_atr = df['ATR'].iloc[-1]

    # --- 4. 메인 차트 시각화 ---
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader(f"📊 {ticker} Price Action & Trendline")
        fig = go.Figure()
        
        # 캔들스틱 차트
        fig.add_trace(go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'], name='Price'
        ))
        
        # 추세선 그리기 (성공 시)
        if slope is not None:
            # 최근 60일치만 선 그리기
            lookback_idx = len(df) - 60
            x_range = df.index[lookback_idx:]
            # y = mx + c (인덱스 기준 계산이므로 변환 필요)
            y_values = [(slope * (i + lookback_idx) + intercept) for i in range(len(x_range))]
            
            fig.add_trace(go.Scatter(
                x=x_range, y=y_values, mode='lines', 
                name='Resistance Line', line=dict(color='orange', width=2, dash='dash')
            ))

        fig.update_layout(height=500, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    # --- 5. 분석 결과 및 포지션 사이징 ---
    with col2:
        st.subheader("🛡️ Signal & Risk")
        
        # 시그널 카드
        if is_breakout:
            st.success(f"🔥 BREAKOUT DETECTED!\nPrice (${current_price:.2f}) > Line (${trendline_price:.2f})")
        else:
            st.info(f"💤 No Signal\nPrice (${current_price:.2f}) < Line (${trendline_price:.2f})")

        st.markdown("---")
        
        # 포지션 사이징 계산
        shares = RiskManager.calculate_position_size(account_balance, risk_pct, current_atr, atr_multiplier)
        total_cost = shares * current_price
        
        st.write("#### 💰 Position Sizing")
        st.metric("Recommended Quantity", f"{shares} Shares")
        st.metric("Estimated Cost", f"${total_cost:,.2f}")
        
        # 세부 데이터
        st.markdown("#### 📉 Metrics")
        st.write(f"- **Current ATR:** ${current_atr:.2f}")
        st.write(f"- **Stop Loss Price:** ${current_price - (current_atr * atr_multiplier):.2f}")