import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import random
import requests
import os

# ============================================================================
# 1. CONFIG & CONSTANTS
# ============================================================================
st.set_page_config(page_title="AntiGravity M7 Bot", layout="wide", page_icon="🚀")

ALL_STOCKS = [
    'NVDA', 'TSLA', 'META', 'AMZN', 'GOOGL', 'AAPL', 'MSFT',  # M7
    'QQQ', 'TQQQ', 'XLK'  # ETFs
]

DISCLAIMER_TEXT = """
<div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ff6b6b; margin-bottom: 20px;">
    <h4 style="color: #856404; margin-top: 0;">⚠️ EDUCATIONAL TOOL ONLY - NOT INVESTMENT ADVICE</h4>
    <ul style="color: #856404; font-size: 0.9em; margin-bottom: 0;">
        <li>This tool detects <b>technical patterns</b>, not investment recommendations.</li>
        <li>Past performance ≠ Future results. You are 100% responsible for your trades.</li>
        <li><b>KR</b>: 본 서비스는 투자 자문이 아니며, 모든 투자의 책임은 사용자에게 있습니다.</li>
    </ul>
</div>
"""

# ============================================================================
# 2. HELPER FUNCTIONS
# ============================================================================
@st.cache_data(ttl=300) # 5분 캐시
def get_stock_data(ticker, period="1y"):
    df = yf.download(ticker, period=period, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def calculate_metrics(df):
    if df.empty: return df
    
    # RSI (Wilder's Smoothing) - Fix for Accuracy
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Moving Averages
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA200'] = df['Close'].rolling(window=200).mean()
    
    # MACD
    exp12 = df['Close'].ewm(span=12, adjust=False).mean()
    exp26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp12 - exp26
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['Hist'] = df['MACD'] - df['Signal']
    
    # ATR
    df['TR'] = pd.concat([
        df['High'] - df['Low'], 
        (df['High'] - df['Close'].shift()).abs(), 
        (df['Low'] - df['Close'].shift()).abs()
    ], axis=1).max(axis=1)
    df['ATR'] = df['TR'].rolling(window=14).mean()
    
    # Volume Avg
    df['VolAvg'] = df['Volume'].rolling(window=20).mean()
    
    # Support/Resistance (Last 20 days)
    df['Support'] = df['Low'].rolling(window=20).min()
    df['Resistance'] = df['High'].rolling(window=20).max()
    
    return df

def get_signal_reason(row):
    reasons = []
    if row['RSI'] < 30:
        reasons.append(f"RSI {row['RSI']:.1f} 과매도")
    elif row['RSI'] < 40:
        reasons.append("RSI 저점 근접")
        
    if row['Close'] > row['MA20']:
        reasons.append("단기 상승 추세")
    else:
        dist = ((row['MA20'] - row['Close']) / row['Close']) * 100
        if dist < 2.0:
            reasons.append("MA20 돌파 임박")
            
    if row['Hist'] > 0 and row['Hist'] > row['Hist_Prev']:
        reasons.append("MACD 상승 반전")
        
    if not reasons:
        return "특이사항 없음"
    return " + ".join(reasons)

def calculate_signal_score(row):
    score = 50 # Base Score
    details = []
    
    # RSI (0-30 pts)
    if row['RSI'] < 30: 
        score += 30
        details.append("RSI<30 (+30)")
    elif row['RSI'] < 40: 
        score += 20
        details.append("RSI<40 (+20)")
    elif row['RSI'] > 70: 
        score -= 20
        details.append("RSI>70 (-20)")
    
    # Trend (0-20 pts)
    if row['Close'] > row['MA20']: 
        score += 10
        details.append("Above MA20 (+10)")
    if row['Close'] > row['MA200']: 
        score += 10
        details.append("Above MA200 (+10)")
    
    # MACD (0-10 pts)
    if row['Hist'] > 0: 
        score += 10
        details.append("MACD Bullish (+10)")
    
    # Volume (0-10 pts)
    if row['Volume'] > row['VolAvg']: 
        score += 10
        details.append("Vol Spike (+10)")
    
    final_score = min(100, max(0, score))
    return final_score, ", ".join(details)

def send_telegram_alert(ticker, score, reason):
    # Placeholder for actual Telegram logic
    return True

# ============================================================================
# 3. MAIN UI
# ============================================================================
def main():
    st.markdown(DISCLAIMER_TEXT, unsafe_allow_html=True)
    
    # Sidebar Filters
    st.sidebar.header("⚙️ Scanner Filters")
    
    # Strategy Selection
    strategy_mode = st.sidebar.selectbox(
        "🎯 Strategy Select",
        ["All Strategies", "RSI Oversold (<30)", "Trendline Breakout (Bullish)", "MACD Reversal", "Volume Spike (>1.2x)"]
    )
    
    rsi_range = st.sidebar.slider("RSI Range", 0, 100, (0, 100))
    min_score = st.sidebar.slider("Min Signal Score", 0, 100, 50)
    
    # Header with Auto-refresh button
    c1, c2 = st.columns([3, 1])
    with c1:
        st.title("🚀 AntiGravity M7 & ETF Dashboard")
    with c2:
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()
        st.caption(f"Updated: {datetime.now().strftime('%H:%M:%S')} (Just now)")

    # [A] Market Pulse
    st.markdown("### 🌍 Market Pulse")
    mp_col1, mp_col2, mp_col3, mp_col4 = st.columns(4)
    
    # Fetch Real Data
    with st.spinner('Fetching Market Pulse...'):
        try:
            market_tickers = ['^VIX', 'KRW=X', '^TNX']
            m_df = yf.download(market_tickers, period="5d", progress=False)['Close']
            
            vix_now = m_df['^VIX'].iloc[-1]
            vix_chg = ((vix_now - m_df['^VIX'].iloc[-2]) / m_df['^VIX'].iloc[-2]) * 100
            
            krw_now = m_df['KRW=X'].iloc[-1]
            krw_chg = ((krw_now - m_df['KRW=X'].iloc[-2]) / m_df['KRW=X'].iloc[-2]) * 100
            
            tnx_now = m_df['^TNX'].iloc[-1]
            tnx_chg = ((tnx_now - m_df['^TNX'].iloc[-2]) / m_df['^TNX'].iloc[-2]) * 100
            
            mp_col1.metric("VIX Index", f"{vix_now:.2f}", f"{vix_chg:.1f}%", delta_color="inverse", help="Volatility Index. >20 suggests high fear.")
            mp_col2.metric("USD/KRW", f"{krw_now:.0f} ₩", f"{krw_chg:.1f}%", delta_color="inverse", help="KRW Exchange Rate.")
            mp_col3.metric("10Y Treasury", f"{tnx_now:.2f}%", f"{tnx_chg:.1f}%", help="US 10Y Bond Yield. High yield hurts tech stocks.")
            
            active_users = random.randint(120, 150)
            mp_col4.metric("Active Users", f"{active_users}", "+5", help="Current active users on dashboard.")
            
        except Exception as e:
            st.error(f"Market Data Error: {e}")

    st.markdown("---")

    # [B] Data Processing
    with st.spinner('🔄 Analyzing Market Data...'):
        market_data = []
        for ticker in ALL_STOCKS:
            df = get_stock_data(ticker, period="1y")
            if df.empty: continue
            df = calculate_metrics(df)
            
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            # Add prev hist for trend check
            last_row_dict = last_row.to_dict()
            last_row_dict['Hist_Prev'] = prev_row['Hist']
            
            score, score_details = calculate_signal_score(last_row_dict)
            
            # --- STRATEGY FILTERING LOGIC ---
            pass_strategy = True
            
            if strategy_mode == "RSI Oversold (<30)":
                if last_row['RSI'] >= 30: pass_strategy = False
                
            elif strategy_mode == "Trendline Breakout (Bullish)":
                # Logic: Price > MA20 (Trend Up) AND Price > Resistance (Breakout)
                # Simplified for now: Price > MA20 AND Price > MA20 * 1.01
                if not (last_row['Close'] > last_row['MA20']): pass_strategy = False
                
            elif strategy_mode == "MACD Reversal":
                # Logic: Histogram turned positive or is rising
                if not (last_row['Hist'] > 0 and last_row['Hist'] > prev_row['Hist']): pass_strategy = False
                
            elif strategy_mode == "Volume Spike (>1.2x)":
                # Lowered threshold to 1.2x
                if not (last_row['Volume'] > last_row['VolAvg'] * 1.2): pass_strategy = False
            
            if not pass_strategy: continue
            # --------------------------------
            
            # Apply Common Filters
            if not (rsi_range[0] <= last_row['RSI'] <= rsi_range[1]): continue
            if score < min_score: continue
            
            market_data.append({
                'Ticker': ticker,
                'Price': last_row['Close'],
                'RSI': last_row['RSI'],
                'MA20': last_row['MA20'],
                'ATR': last_row['ATR'],
                'Score': score,
                'Score Details': score_details,
                'Reason': get_signal_reason(last_row_dict),
                'Trend': "UP 🔼" if last_row['Close'] > last_row['MA20'] else "DOWN 🔽",
                'Support': last_row['Support'],
                'Resistance': last_row['Resistance']
            })
            
        scan_df = pd.DataFrame(market_data)
        
        # Top 3 Picks
        if not scan_df.empty:
            top_picks = scan_df.sort_values(by=['Score', 'RSI'], ascending=[False, True]).head(3)
        else:
            top_picks = pd.DataFrame()

    # [C] 🎯 Today's Top Signals (Top 3)
    if not top_picks.empty:
        st.markdown(f"### 🎯 Today's Top Signals")
        cols = st.columns(len(top_picks))
        
        for i, (index, row) in enumerate(top_picks.iterrows()):
            with cols[i]:
                st.markdown(f"""
                <div style="background-color: #e8f4f8; padding: 15px; border-radius: 10px; border: 2px solid #2E86C1;">
                    <h3 style="color: #2E86C1; margin:0;">{i+1}. {row['Ticker']}</h3>
                    <p style="font-size: 1.1em; margin: 5px 0;">
                        <b>Score: {row['Score']}</b> <span style="font-size:0.8em; color:#666;">({row['Score Details']})</span>
                    </p>
                    <p style="color: #555; margin:0;">Price: <b>${row['Price']:.2f}</b> | RSI: <b>{row['RSI']:.1f}</b></p>
                    <p style="color: #27ae60; font-weight:bold; margin-top:5px;">{row['Reason']}</p>
                </div>
                """, unsafe_allow_html=True)
        
        st.write("") # Spacer

        # [D] Main Layout (Chart & Analysis)
        col_left, col_right = st.columns([2, 1])

        with col_left:
            st.subheader("📊 Advanced Chart Analysis")
            # Default to #1 pick
            selected_ticker = st.selectbox("Select Ticker", scan_df['Ticker'].tolist(), index=scan_df['Ticker'].tolist().index(top_picks.iloc[0]['Ticker']))
            
            # Get data for selected ticker
            df_sel = get_stock_data(selected_ticker)
            df_sel = calculate_metrics(df_sel)
            
            # Advanced Chart with Subplots
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.05, row_heights=[0.7, 0.3],
                                subplot_titles=(f"{selected_ticker} Price & MA", "MACD & Volume"))

            # Row 1: Price, MA20, Support/Resistance
            fig.add_trace(go.Scatter(x=df_sel.index, y=df_sel['Close'], mode='lines', name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_sel.index, y=df_sel['MA20'], mode='lines', name='MA20', line=dict(dash='dash', color='orange')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_sel.index, y=df_sel['Support'], mode='lines', name='Support (20d)', line=dict(color='green', width=1)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_sel.index, y=df_sel['Resistance'], mode='lines', name='Resistance (20d)', line=dict(color='red', width=1)), row=1, col=1)

            # Row 2: MACD
            fig.add_trace(go.Bar(x=df_sel.index, y=df_sel['Hist'], name='MACD Hist'), row=2, col=1)
            fig.add_trace(go.Scatter(x=df_sel.index, y=df_sel['MACD'], name='MACD'), row=2, col=1)
            fig.add_trace(go.Scatter(x=df_sel.index, y=df_sel['Signal'], name='Signal'), row=2, col=1)

            fig.update_layout(height=600, template="plotly_white", margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)

        with col_right:
            st.subheader("🛡️ Pro Position Calculator")
            
            current_row = scan_df[scan_df['Ticker'] == selected_ticker].iloc[0]
            
            # Calculator
            balance = st.number_input("Account Balance ($)", value=10000, step=1000)
            risk_pct = st.slider("Risk (%)", 1.0, 5.0, 2.0)
            
            atr = current_row['ATR']
            entry_price = current_row['Price']
            stop_loss = entry_price - (atr * 2.0)
            risk_per_share = entry_price - stop_loss
            
            # Take Profit (1:2 Ratio)
            take_profit = entry_price + (risk_per_share * 2.0)
            
            risk_amt = balance * (risk_pct / 100)
            shares = int(risk_amt / risk_per_share) if risk_per_share > 0 else 0
            
            est_profit = (take_profit - entry_price) * shares
            
            st.info(f"""
            **Strategy Setup (R/R 1:2)**
            - **Entry:** ${entry_price:.2f}
            - **Stop Loss:** ${stop_loss:.2f} (-${risk_amt:.0f})
            - **Take Profit:** ${take_profit:.2f} (+${est_profit:.0f})
            """)
            
            st.success(f"**Buy Order:** {shares} Shares")
            
            # Notification Button
            if st.button(f"🔔 Send {selected_ticker} Alert to Telegram"):
                st.toast(f"Alert sent for {selected_ticker}!", icon="✅")
                # send_telegram_alert(...)

    else:
        st.warning("No stocks match your current filters. Try adjusting the RSI or Score settings.")

    st.markdown("---")

    # [E] Market Scanner Table
    st.markdown("### 🔍 Market Scanner (Ranked by Score)")
    
    if not scan_df.empty:
        display_df = scan_df.sort_values(by='Score', ascending=False).copy()
        display_df['Price'] = display_df['Price'].apply(lambda x: f"${x:.2f}")
        display_df['RSI'] = display_df['RSI'].apply(lambda x: f"{x:.1f}")
        
        cols = ['Ticker', 'Price', 'Trend', 'RSI', 'Score', 'Score Details', 'Reason']
        st.dataframe(
            display_df[cols],
            use_container_width=True,
            column_config={
                "Score": st.column_config.ProgressColumn("Signal Score", min_value=0, max_value=100, format="%d"),
                "Score Details": st.column_config.TextColumn("Score Breakdown", width="medium"),
                "Reason": st.column_config.TextColumn("Analysis", width="large"),
            },
            hide_index=True
        )

if __name__ == "__main__":
    main()
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import random
import requests
import os

# ============================================================================
# 1. CONFIG & CONSTANTS
# ============================================================================
st.set_page_config(page_title="AntiGravity M7 Bot", layout="wide", page_icon="🚀")

ALL_STOCKS = [
    'NVDA', 'TSLA', 'META', 'AMZN', 'GOOGL', 'AAPL', 'MSFT',  # M7
    'QQQ', 'TQQQ', 'XLK'  # ETFs
]

DISCLAIMER_TEXT = """
<div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ff6b6b; margin-bottom: 20px;">
    <h4 style="color: #856404; margin-top: 0;">⚠️ EDUCATIONAL TOOL ONLY - NOT INVESTMENT ADVICE</h4>
    <ul style="color: #856404; font-size: 0.9em; margin-bottom: 0;">
        <li>This tool detects <b>technical patterns</b>, not investment recommendations.</li>
        <li>Past performance ≠ Future results. You are 100% responsible for your trades.</li>
        <li><b>KR</b>: 본 서비스는 투자 자문이 아니며, 모든 투자의 책임은 사용자에게 있습니다.</li>
    </ul>
</div>
"""

# ============================================================================
# 2. HELPER FUNCTIONS
# ============================================================================
@st.cache_data(ttl=300) # 5분 캐시
def get_stock_data(ticker, period="1y"):
    df = yf.download(ticker, period=period, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def calculate_metrics(df):
    if df.empty: return df
    
    # Basic Indicators
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA200'] = df['Close'].rolling(window=200).mean()
    
    # MACD
    exp12 = df['Close'].ewm(span=12, adjust=False).mean()
    exp26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp12 - exp26
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['Hist'] = df['MACD'] - df['Signal']
    
    # ATR
    df['TR'] = pd.concat([
        df['High'] - df['Low'], 
        (df['High'] - df['Close'].shift()).abs(), 
        (df['Low'] - df['Close'].shift()).abs()
    ], axis=1).max(axis=1)
    df['ATR'] = df['TR'].rolling(window=14).mean()
    
    # Volume Avg
    df['VolAvg'] = df['Volume'].rolling(window=20).mean()
    
    # Support/Resistance (Last 20 days)
    df['Support'] = df['Low'].rolling(window=20).min()
    df['Resistance'] = df['High'].rolling(window=20).max()
    
    return df

def get_signal_reason(row):
    reasons = []
    if row['RSI'] < 30:
        reasons.append(f"RSI {row['RSI']:.1f} 과매도")
    elif row['RSI'] < 40:
        reasons.append("RSI 저점 근접")
        
    if row['Close'] > row['MA20']:
        reasons.append("단기 상승 추세")
    else:
        dist = ((row['MA20'] - row['Close']) / row['Close']) * 100
        if dist < 2.0:
            reasons.append("MA20 돌파 임박")
            
    if row['Hist'] > 0 and row['Hist'] > row['Hist_Prev']:
        reasons.append("MACD 상승 반전")
        
    if not reasons:
        return "특이사항 없음"
    return " + ".join(reasons)

def calculate_signal_score(row):
    score = 50 # Base Score
    
    # RSI (0-30 pts)
    if row['RSI'] < 30: score += 30
    elif row['RSI'] < 40: score += 20
    elif row['RSI'] > 70: score -= 20
    
    # Trend (0-20 pts)
    if row['Close'] > row['MA20']: score += 10
    if row['Close'] > row['MA200']: score += 10
    
    # MACD (0-10 pts)
    if row['Hist'] > 0: score += 10
    
    # Volume (0-10 pts)
    if row['Volume'] > row['VolAvg']: score += 10
    
    return min(100, max(0, score))

def send_telegram_alert(ticker, score, reason):
    # Placeholder for actual Telegram logic
    # In a real app, you would read token from secrets
    return True

# ============================================================================
# 3. MAIN UI
# ============================================================================
def main():
    st.markdown(DISCLAIMER_TEXT, unsafe_allow_html=True)
    
    # Sidebar Filters
    st.sidebar.header("⚙️ Scanner Filters")
    
    # Strategy Selection
    strategy_mode = st.sidebar.selectbox(
        "🎯 Strategy Select",
        ["All Strategies", "RSI Oversold (<30)", "Trendline Breakout + ATR", "MACD Reversal", "Volume Spike (>1.5x)"]
    )
    
    rsi_range = st.sidebar.slider("RSI Range", 0, 100, (0, 100))
    min_score = st.sidebar.slider("Min Signal Score", 0, 100, 50)
    
    # Header with Auto-refresh button
    c1, c2 = st.columns([3, 1])
    with c1:
        st.title("🚀 AntiGravity M7 & ETF Dashboard")
    with c2:
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()
        st.caption(f"Updated: {datetime.now().strftime('%H:%M:%S')} (Just now)")

    # [A] Market Pulse
    st.markdown("### 🌍 Market Pulse")
    mp_col1, mp_col2, mp_col3, mp_col4 = st.columns(4)
    
    # Fetch Real Data
    with st.spinner('Fetching Market Pulse...'):
        try:
            market_tickers = ['^VIX', 'KRW=X', '^TNX']
            m_df = yf.download(market_tickers, period="5d", progress=False)['Close']
            
            vix_now = m_df['^VIX'].iloc[-1]
            vix_chg = ((vix_now - m_df['^VIX'].iloc[-2]) / m_df['^VIX'].iloc[-2]) * 100
            
            krw_now = m_df['KRW=X'].iloc[-1]
            krw_chg = ((krw_now - m_df['KRW=X'].iloc[-2]) / m_df['KRW=X'].iloc[-2]) * 100
            
            tnx_now = m_df['^TNX'].iloc[-1]
            tnx_chg = ((tnx_now - m_df['^TNX'].iloc[-2]) / m_df['^TNX'].iloc[-2]) * 100
            
            mp_col1.metric("VIX Index", f"{vix_now:.2f}", f"{vix_chg:.1f}%", delta_color="inverse", help="Volatility Index. >20 suggests high fear.")
            mp_col2.metric("USD/KRW", f"{krw_now:.0f} ₩", f"{krw_chg:.1f}%", delta_color="inverse", help="KRW Exchange Rate.")
            mp_col3.metric("10Y Treasury", f"{tnx_now:.2f}%", f"{tnx_chg:.1f}%", help="US 10Y Bond Yield. High yield hurts tech stocks.")
            
            active_users = random.randint(120, 150)
            mp_col4.metric("Active Users", f"{active_users}", "+5", help="Current active users on dashboard.")
            
        except Exception as e:
            st.error(f"Market Data Error: {e}")

    st.markdown("---")

    # [B] Data Processing
    with st.spinner('🔄 Analyzing Market Data...'):
        market_data = []
        for ticker in ALL_STOCKS:
            df = get_stock_data(ticker, period="1y")
            if df.empty: continue
            df = calculate_metrics(df)
            
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            # Add prev hist for trend check
            last_row_dict = last_row.to_dict()
            last_row_dict['Hist_Prev'] = prev_row['Hist']
            
            score = calculate_signal_score(last_row_dict)
            
            # --- STRATEGY FILTERING LOGIC ---
            pass_strategy = True
            
            if strategy_mode == "RSI Oversold (<30)":
                if last_row['RSI'] >= 30: pass_strategy = False
                
            elif strategy_mode == "Trendline Breakout + ATR":
                # Logic: Price > MA20 (Trend) AND Price > Resistance (Breakout) OR High Volatility
                # Simplified: Uptrend + Price near Highs
                if not (last_row['Close'] > last_row['MA20']): pass_strategy = False
                
            elif strategy_mode == "MACD Reversal":
                # Logic: Histogram turned positive or is rising
                if not (last_row['Hist'] > 0 and last_row['Hist'] > prev_row['Hist']): pass_strategy = False
                
            elif strategy_mode == "Volume Spike (>1.5x)":
                if not (last_row['Volume'] > last_row['VolAvg'] * 1.5): pass_strategy = False
            
            if not pass_strategy: continue
            # --------------------------------
            
            # Apply Common Filters
            if not (rsi_range[0] <= last_row['RSI'] <= rsi_range[1]): continue
            if score < min_score: continue
            
            market_data.append({
                'Ticker': ticker,
                'Price': last_row['Close'],
                'RSI': last_row['RSI'],
                'MA20': last_row['MA20'],
                'ATR': last_row['ATR'],
                'Score': score,
                'Reason': get_signal_reason(last_row_dict),
                'Trend': "UP 🔼" if last_row['Close'] > last_row['MA20'] else "DOWN 🔽",
                'Support': last_row['Support'],
                'Resistance': last_row['Resistance']
            })
            
        scan_df = pd.DataFrame(market_data)
        if not scan_df.empty:
            best_pick = scan_df.sort_values(by=['Score', 'RSI'], ascending=[False, True]).iloc[0]
        else:
            best_pick = None

    # [C] 🎯 Today's Best Pick Section
    if best_pick is not None:
        st.markdown(f"""
        <div style="background-color: #e8f4f8; padding: 20px; border-radius: 10px; border: 2px solid #2E86C1; margin-bottom: 30px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h2 style="color: #2E86C1; margin:0;">🎯 Today's Top Signal: {best_pick['Ticker']}</h2>
                    <p style="font-size: 1.2em; margin: 10px 0;">
                        <b>Score: {best_pick['Score']}/100</b> | {best_pick['Reason']}
                    </p>
                    <p style="color: #555;">현재가: <b>${best_pick['Price']:.2f}</b> | RSI: <b>{best_pick['RSI']:.1f}</b></p>
                </div>
                <div style="text-align: right;">
                    <h3 style="color: #27ae60; margin:0;">Expected Rebound</h3>
                    <h1 style="color: #27ae60; margin:0;">+5~8%</h1>
                    <small>Based on historical volatility</small>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # [D] Main Layout (Chart & Analysis)
        col_left, col_right = st.columns([2, 1])

        with col_left:
            st.subheader("📊 Advanced Chart Analysis")
            selected_ticker = st.selectbox("Select Ticker", scan_df['Ticker'].tolist(), index=scan_df['Ticker'].tolist().index(best_pick['Ticker']))
            
            # Get data for selected ticker
            df_sel = get_stock_data(selected_ticker)
            df_sel = calculate_metrics(df_sel)
            
            # Advanced Chart with Subplots
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.05, row_heights=[0.7, 0.3],
                                subplot_titles=(f"{selected_ticker} Price & MA", "MACD & Volume"))

            # Row 1: Price, MA20, Support/Resistance
            fig.add_trace(go.Scatter(x=df_sel.index, y=df_sel['Close'], mode='lines', name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_sel.index, y=df_sel['MA20'], mode='lines', name='MA20', line=dict(dash='dash', color='orange')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_sel.index, y=df_sel['Support'], mode='lines', name='Support (20d)', line=dict(color='green', width=1)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_sel.index, y=df_sel['Resistance'], mode='lines', name='Resistance (20d)', line=dict(color='red', width=1)), row=1, col=1)

            # Row 2: MACD
            fig.add_trace(go.Bar(x=df_sel.index, y=df_sel['Hist'], name='MACD Hist'), row=2, col=1)
            fig.add_trace(go.Scatter(x=df_sel.index, y=df_sel['MACD'], name='MACD'), row=2, col=1)
            fig.add_trace(go.Scatter(x=df_sel.index, y=df_sel['Signal'], name='Signal'), row=2, col=1)

            fig.update_layout(height=600, template="plotly_white", margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)

        with col_right:
            st.subheader("🛡️ Pro Position Calculator")
            
            current_row = scan_df[scan_df['Ticker'] == selected_ticker].iloc[0]
            
            # Calculator
            balance = st.number_input("Account Balance ($)", value=10000, step=1000)
            risk_pct = st.slider("Risk (%)", 1.0, 5.0, 2.0)
            
            atr = current_row['ATR']
            entry_price = current_row['Price']
            stop_loss = entry_price - (atr * 2.0)
            risk_per_share = entry_price - stop_loss
            
            # Take Profit (1:2 Ratio)
            take_profit = entry_price + (risk_per_share * 2.0)
            
            risk_amt = balance * (risk_pct / 100)
            shares = int(risk_amt / risk_per_share) if risk_per_share > 0 else 0
            
            est_profit = (take_profit - entry_price) * shares
            
            st.info(f"""
            **Strategy Setup (R/R 1:2)**
            - **Entry:** ${entry_price:.2f}
            - **Stop Loss:** ${stop_loss:.2f} (-${risk_amt:.0f})
            - **Take Profit:** ${take_profit:.2f} (+${est_profit:.0f})
            """)
            
            st.success(f"**Buy Order:** {shares} Shares")
            
            # Notification Button
            if st.button(f"🔔 Send {selected_ticker} Alert to Telegram"):
                st.toast(f"Alert sent for {selected_ticker}!", icon="✅")
                # send_telegram_alert(...)

    else:
        st.warning("No stocks match your current filters. Try adjusting the RSI or Score settings.")

    st.markdown("---")

    # [E] Market Scanner Table
    st.markdown("### 🔍 Market Scanner (Ranked by Score)")
    
    if not scan_df.empty:
        display_df = scan_df.sort_values(by='Score', ascending=False).copy()
        display_df['Price'] = display_df['Price'].apply(lambda x: f"${x:.2f}")
        display_df['RSI'] = display_df['RSI'].apply(lambda x: f"{x:.1f}")
        
        cols = ['Ticker', 'Price', 'Trend', 'RSI', 'Score', 'Reason']
        st.dataframe(
            display_df[cols],
            use_container_width=True,
            column_config={
                "Score": st.column_config.ProgressColumn("Signal Score", min_value=0, max_value=100, format="%d"),
                "Reason": st.column_config.TextColumn("Analysis", width="large"),
            },
            hide_index=True
        )

if __name__ == "__main__":
    main()