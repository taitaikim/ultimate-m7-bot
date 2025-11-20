"""
M7 Bot - Streamlit Dashboard (V2.2)
Visual Backtesting & Signal Monitoring
"""

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import os
from dotenv import load_dotenv
import ta

# Load environment variables
load_dotenv()

# Import DB Manager
from m7_cloud import DBManager

# ============================================================================
# ⚠️ LEGAL DISCLAIMER (법적 면책 조항)
# ============================================================================
DISCLAIMER_HTML = """
<div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; border-left: 5px solid #ffc107; margin-bottom: 20px;">
    <h4 style="color: #856404; margin-top: 0;">⚠️ EDUCATIONAL TOOL ONLY - NOT INVESTMENT ADVICE</h4>
    <ul style="color: #856404; font-size: 0.9em; margin-bottom: 0;">
        <li><strong>Technical Patterns Only:</strong> This tool detects technical patterns, not investment recommendations.</li>
        <li><strong>Past Performance ≠ Future Results:</strong> Historical data does not guarantee future profits.</li>
        <li><strong>Your Responsibility:</strong> You are 100% responsible for your trading decisions.</li>
        <hr style="border-color: #e0a800; margin: 10px 0;">
        <li><strong>투자 유의사항:</strong> 본 서비스는 금융투자업 미등록 교육 도구이며, 매수/매도에 대한 추천이 아닙니다.</li>
        <li><strong>책임의 한계:</strong> 모든 투자의 결과(손실 포함)는 <strong>사용자 본인</strong>에게 귀속됩니다.</li>
    </ul>
</div>
"""

# ============================================================================
# CONFIGURATION
# ============================================================================
st.set_page_config(
    page_title="M7 Bot Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
@st.cache_data(ttl=300)
def load_signals_data(limit: int = 100) -> pd.DataFrame:
    """Supabase에서 실시간 신호 데이터 로드"""
    try:
        # Streamlit Cloud Secrets 우선 처리
        try:
            if 'SUPABASE_URL' in st.secrets:
                os.environ['SUPABASE_URL'] = st.secrets['SUPABASE_URL']
                os.environ['SUPABASE_KEY'] = st.secrets['SUPABASE_KEY']
        except Exception:
            pass
        
        db = DBManager()
        response = db.supabase.table("m7_signals").select("*").order("created_at", desc=True).limit(limit).execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            df['created_at'] = pd.to_datetime(df['created_at'])
            return df
        return pd.DataFrame()
            
    except Exception as e:
        st.error(f"❌ 데이터 로드 실패: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def run_technical_backtest(ticker: str, period: str = "6mo"):
    """
    과거 데이터 기반 기술적 백테스팅 (시각화용)
    """
    try:
        df = yf.download(ticker, period=period, progress=False)
        if df.empty:
            return None, None, None
            
        # 지표 계산 (main.py 로직과 동일하게 적용)
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # 신호 발굴
        buy_signals = []
        sell_signals = []
        
        # 그룹별 RSI 기준 (기본값 적용)
        buy_rsi_th = 30
        if ticker in ['NVDA', 'TSLA', 'TQQQ']: buy_rsi_th = 25
        elif ticker in ['AAPL', 'MSFT', 'QQQ']: buy_rsi_th = 35
        
        for i in range(60, len(df)):
            # 매수 로직: RSI 과매도 + 골든크로스 근처
            if df['RSI'].iloc[i] < buy_rsi_th:
                buy_signals.append((df.index[i], df['Close'].iloc[i]))
            
            # 매도 로직: RSI 과매수 (단순화)
            elif df['RSI'].iloc[i] > 70:
                sell_signals.append((df.index[i], df['Close'].iloc[i]))
                
        return df, buy_signals, sell_signals
        
    except Exception as e:
        st.error(f"백테스팅 오류: {e}")
        return None, None, None

def plot_backtest_chart(ticker, df, buy_signals, sell_signals):
    """Plotly를 이용한 인터랙티브 차트 그리기"""
    fig = go.Figure()

    # 1. 주가 라인
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Close'],
        mode='lines', name='Price',
        line=dict(color='#1f77b4', width=2)
    ))

    # 2. 매수 신호 (초록색 상승 화살표)
    if buy_signals:
        buy_dates, buy_prices = zip(*buy_signals)
        fig.add_trace(go.Scatter(
            x=buy_dates, y=buy_prices,
            mode='markers', name='Buy Signal',
            marker=dict(symbol='triangle-up', size=12, color='green', line=dict(width=1, color='darkgreen'))
        ))

    # 3. 매도 신호 (빨간색 하락 화살표)
    if sell_signals:
        sell_dates, sell_prices = zip(*sell_signals)
        fig.add_trace(go.Scatter(
            x=sell_dates, y=sell_prices,
            mode='markers', name='Sell Signal',
            marker=dict(symbol='triangle-down', size=12, color='red', line=dict(width=1, color='darkred'))
        ))

    fig.update_layout(
        title=f"📈 {ticker} Technical Backtest (Recent 6 Months)",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        template="plotly_white",
        hovermode="x unified",
        height=500
    )
    
    return fig

# ============================================================================
# MAIN DASHBOARD
# ============================================================================
def main() -> None:
    st.title("🚀 M7 Bot Dashboard")
    st.markdown(DISCLAIMER_HTML, unsafe_allow_html=True)
    
    # 탭 구성
    tab1, tab2 = st.tabs(["📊 실시간 신호", "📈 차트 백테스팅"])
    
    # --- TAB 1: 실시간 신호 모니터링 ---
    with tab1:
        with st.sidebar:
            st.header("⚙️ 설정")
            if st.button("🔄 데이터 새로고침", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
            st.markdown("---")
            data_limit = st.slider("표시할 신호 개수", 10, 200, 100, 10)
            
        # Load Data
        with st.spinner("📡 클라우드 데이터를 불러오는 중..."):
            df = load_signals_data(limit=data_limit)
        
        if not df.empty:
            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            today_signals = len(df[df['created_at'].dt.date == datetime.now().date()])
            strong_buys = len(df[df['signal_type'].str.contains('STRONG|TECHNICAL', case=False, na=False)])
            
            col1.metric("총 신호", f"{len(df)}", f"+{today_signals} Today")
            col2.metric("패턴 포착", f"{strong_buys}", "Buy Signals")
            col3.metric("모니터링", "10개", "M7 + ETFs")
            
            # Data Table
            st.subheader("📋 실시간 신호 내역")
            st.dataframe(
                df[['created_at', 'ticker', 'signal_type', 'entry_price', 'filters']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "created_at": st.column_config.DatetimeColumn("시간", format="MM/DD HH:mm"),
                    "entry_price": st.column_config.NumberColumn("가격", format="$%.2f"),
                    "filters": "필터 상태"
                }
            )
        else:
            st.info("데이터가 없습니다. 봇이 실행되면 신호가 표시됩니다.")

    # --- TAB 2: 차트 백테스팅 (Visual Proof) ---
    with tab2:
        st.subheader("🔍 과거 차트 복기 (Visual Proof)")
        st.info("💡 봇의 알고리즘이 과거에 적용되었다면 어디서 매수했을지 시각적으로 확인합니다.")
        
        col_sel, col_blank = st.columns([1, 3])
        with col_sel:
            selected_ticker = st.selectbox(
                "분석할 종목 선택", 
                ['NVDA', 'TSLA', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'QQQ', 'TQQQ', 'XLK']
            )
        
        if selected_ticker:
            with st.spinner(f"{selected_ticker} 과거 데이터 분석 중..."):
                hist_df, buys, sells = run_technical_backtest(selected_ticker)
                
                if hist_df is not None:
                    # 차트 그리기
                    fig = plot_backtest_chart(selected_ticker, hist_df, buys, sells)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 통계 표시
                    st.markdown(f"""
                    <div style='display: flex; gap: 20px; justify-content: center;'>
                        <div style='background:#e8f5e9; padding:10px 20px; border-radius:10px;'>
                            <span style='font-size:1.2em;'>🟢 매수 기회: <b>{len(buys)}회</b></span>
                        </div>
                        <div style='background:#ffebee; padding:10px 20px; border-radius:10px;'>
                            <span style='font-size:1.2em;'>🔴 매도 기회: <b>{len(sells)}회</b></span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error("데이터를 불러올 수 없습니다.")

if __name__ == "__main__":
    main()
