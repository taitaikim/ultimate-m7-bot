"""
M7 Bot - Streamlit Dashboard (V2.3 Trend Following)
Enhanced UI/UX & Trend Following Backtest Logic
"""

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import os
from dotenv import load_dotenv

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
        try:
            if hasattr(st, "secrets") and "SUPABASE_URL" in st.secrets:
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
    과거 데이터 기반 기술적 백테스팅 (로직 개선: 추세 추종)
    """
    try:
        # [수정] auto_adjust=True 추가 (주식 분할/배당 락 데이터 보정)
        df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
        
        if df.empty:
            return None, None, None
            
        # MultiIndex 처리
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # 지표 계산
        df['MA20'] = df['Close'].rolling(window=20).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        buy_signals = []
        sell_signals = []
        
        # 포지션 보유 상태 확인용 변수
        holding = False 
        
        for i in range(20, len(df)):
            price = df['Close'].iloc[i]
            rsi = df['RSI'].iloc[i]
            ma20 = df['MA20'].iloc[i]
            
            # 🟢 매수 로직: RSI가 과매도 구간(40) 아래일 때 (저점 매수)
            if not holding and rsi < 40:
                buy_signals.append((df.index[i], price))
                holding = True
            
            # 🔴 매도 로직: (수정됨) "추세 추종형 매도"
            # 단순히 RSI가 높다고 파는 게 아니라, 가격이 20일 이동평균선 아래로 깨질 때 매도
            # (상승세를 최대한 즐기다가 꺾일 때 파는 전략)
            elif holding and price < ma20 and rsi > 50:
                sell_signals.append((df.index[i], price))
                holding = False
                
        return df, buy_signals, sell_signals
        
    except Exception as e:
        print(f"백테스팅 오류: {e}")
        return None, None, None

def plot_backtest_chart(ticker, df, buy_signals, sell_signals):
    """Plotly 차트 그리기"""
    fig = go.Figure()

    # 주가 라인
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Close'],
        mode='lines', name='Price',
        line=dict(color='#1f77b4', width=2)
    ))

    # 매수 신호 (초록)
    if buy_signals:
        buy_dates, buy_prices = zip(*buy_signals)
        fig.add_trace(go.Scatter(
            x=buy_dates, y=buy_prices,
            mode='markers', name='Potential Buy',
            marker=dict(symbol='triangle-up', size=12, color='green', line=dict(width=1, color='darkgreen'))
        ))

    # 매도 신호 (빨강)
    if sell_signals:
        sell_dates, sell_prices = zip(*sell_signals)
        fig.add_trace(go.Scatter(
            x=sell_dates, y=sell_prices,
            mode='markers', name='Potential Sell',
            marker=dict(symbol='triangle-down', size=12, color='red', line=dict(width=1, color='darkred'))
        ))

    fig.update_layout(
        title=f"📈 {ticker} Market Timing Simulation (Last 6 Months)",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        template="plotly_white",
        hovermode="x unified",
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

# ============================================================================
# MAIN DASHBOARD
# ============================================================================
def main() -> None:
    st.title("🚀 M7 Bot Dashboard")
    st.markdown(DISCLAIMER_HTML, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📊 실시간 신호", "📈 차트 백테스팅"])
    
    # --- TAB 1: 실시간 신호 ---
    with tab1:
        with st.sidebar:
            st.header("⚙️ 설정")
            if st.button("🔄 데이터 새로고침", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
            st.markdown("---")
            data_limit = st.slider("표시할 신호 개수", 10, 200, 100, 10)
            
        # Load Data
        with st.spinner("📡 클라우드 데이터 로딩 중..."):
            df = load_signals_data(limit=data_limit)
        
        if not df.empty:
            # 요약 지표
            col1, col2, col3, col4 = st.columns(4)
            today_signals = len(df[df['created_at'].dt.date == datetime.now().date()])
            strong_buys = len(df[df['signal_type'].str.contains('STRONG|TECHNICAL', case=False, na=False)])
            
            col1.metric("총 신호", f"{len(df)}", f"+{today_signals} Today")
            col2.metric("패턴 포착", f"{strong_buys}", "Opportunities")
            col3.metric("모니터링", "10개", "M7 + ETFs")
            
            # [UI 개선] 깔끔한 테이블 표시
            st.subheader("📋 실시간 신호 내역")
            
            # 표시용 데이터프레임 가공
            display_df = df.copy()
            
            # 1. 필요한 컬럼만 선택
            display_df = display_df[['created_at', 'ticker', 'signal_type', 'entry_price']]
            
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "created_at": st.column_config.DatetimeColumn(
                        "발생 시간",
                        format="MM/DD HH:mm",
                    ),
                    "ticker": "종목",
                    "signal_type": st.column_config.TextColumn(
                        "신호 유형",
                        width="medium"
                    ),
                    "entry_price": st.column_config.NumberColumn(
                        "진입가",
                        format="$%.2f"
                    )
                }
            )
            
            # [UI 개선] 지저분한 JSON 필터 정보는 클릭했을 때만 보이게 숨김
            with st.expander("🔍 상세 필터 데이터 확인하기 (디버깅용)"):
                st.dataframe(df)
                
        else:
            st.info("데이터베이스에 저장된 신호가 없습니다. 봇이 실행되면 표시됩니다.")

    # --- TAB 2: 차트 백테스팅 ---
    with tab2:
        st.subheader("🔍 과거 차트 복기 (Visual Proof)")
        st.info("💡 봇의 매매 로직(RSI + 추세)이 과거 차트에서 어떻게 작동했는지 시각화합니다.")
        
        col_sel, col_blank = st.columns([1, 3])
        with col_sel:
            selected_ticker = st.selectbox(
                "분석할 종목 선택", 
                ['TQQQ', 'NVDA', 'TSLA', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'QQQ', 'XLK']
            )
        
        if selected_ticker:
            with st.spinner(f"{selected_ticker} 데이터 분석 중..."):
                hist_df, buys, sells = run_technical_backtest(selected_ticker)
                
                if hist_df is not None:
                    fig = plot_backtest_chart(selected_ticker, hist_df, buys, sells)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.markdown(f"""
                    <div style='display: flex; gap: 20px; justify-content: center; margin-top: 10px;'>
                        <div style='background:#e8f5e9; padding:15px 30px; border-radius:10px; border:1px solid #c8e6c9;'>
                            <span style='font-size:1.1em; color:#2e7d32;'>🟢 매수 기회: <b>{len(buys)}회</b></span>
                        </div>
                        <div style='background:#ffebee; padding:15px 30px; border-radius:10px; border:1px solid #ffcdd2;'>
                            <span style='font-size:1.1em; color:#c62828;'>🔴 매도 기회: <b>{len(sells)}회</b></span>
                        </div>
                    </div>
                    <p style='text-align: center; color: gray; font-size: 0.8em; margin-top: 10px;'>
                        * 시각화용 시뮬레이션이며 실제 수익률과는 다를 수 있습니다.
                    </p>
                    """, unsafe_allow_html=True)
                else:
                    st.warning("데이터를 불러올 수 없습니다.")

if __name__ == "__main__":
    main()