"""
M7 Bot - Streamlit Dashboard (V4.1 Trendline + ATR)
Trendline Breakdown Strategy with ATR Position Sizing
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
def run_technical_backtest(ticker: str, period: str = "1y", account_size: float = 100000):
    """
    과거 데이터 기반 기술적 백테스팅 (로직 v4.1: 추세선 브레이크다운 + ATR 포지션 사이징)
    """
    try:
        # 일봉 데이터
        df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
        
        if df.empty:
            return None, None, None, None
            
        # MultiIndex 처리
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # 이동평균선 계산 (추세선 대용)
        df['MA20'] = df['Close'].rolling(window=20).mean()
        
        # ATR 계산 (14일)
        df['H-L'] = df['High'] - df['Low']
        df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
        df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
        df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
        df['ATR'] = df['TR'].rolling(window=14).mean()
        
        buy_signals = []
        sell_signals = []
        position_sizes = []  # ATR 기반 포지션 크기
        
        # 포지션 보유 상태
        holding = False 
        entry_price = None
        
        # 리스크 설정 (계좌의 1.5%)
        risk_amount = account_size * 0.015
        
        for i in range(20, len(df)):
            price = df['Close'].iloc[i]
            ma20 = df['MA20'].iloc[i]
            atr = df['ATR'].iloc[i]
            
            # 🟢 매수 로직: 가격이 추세선(MA20) 위에 있을 때
            if not holding and pd.notna(atr):
                if price > ma20:
                    # ATR 기반 포지션 사이징
                    # 포지션 크기 = 리스크 금액 / (ATR × 2)
                    shares = int(risk_amount / (atr * 2))
                    position_value = shares * price
                    position_pct = (position_value / account_size) * 100
                    
                    buy_signals.append((df.index[i], price))
                    position_sizes.append({
                        'date': df.index[i],
                        'price': price,
                        'atr': atr,
                        'shares': shares,
                        'position_value': position_value,
                        'position_pct': position_pct
                    })
                    holding = True
                    entry_price = price
            
            # 🔴 매도 로직: 가격이 추세선(MA20)을 하향 돌파
            elif holding:
                prev_price = df['Close'].iloc[i-1]
                prev_ma20 = df['MA20'].iloc[i-1]
                
                # 추세선 하향 돌파 (Breakdown)
                if prev_price >= prev_ma20 and price < ma20:
                    sell_signals.append((df.index[i], price))
                    holding = False
                    entry_price = None
                
        return df, buy_signals, sell_signals, position_sizes
        
    except Exception as e:
        print(f"백테스팅 오류: {e}")
        return None, None, None, None

def plot_backtest_chart(ticker, df, buy_signals, sell_signals):
    """Plotly 차트 그리기"""
    fig = go.Figure()

    # 주가 라인
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Close'],
        mode='lines', name='Price',
        line=dict(color='#1f77b4', width=2)
    ))
    
    # 추세선 (MA20)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['MA20'],
        mode='lines', name='Trendline (MA20)',
        line=dict(color='red', width=2, dash='solid')
    ))

    # 매수 신호 (초록)
    if buy_signals:
        buy_dates, buy_prices = zip(*buy_signals)
        fig.add_trace(go.Scatter(
            x=buy_dates, y=buy_prices,
            mode='markers', name='Buy (Above Trendline)',
            marker=dict(symbol='triangle-up', size=12, color='green', line=dict(width=1, color='darkgreen'))
        ))

    # 매도 신호 (빨강)
    if sell_signals:
        sell_dates, sell_prices = zip(*sell_signals)
        fig.add_trace(go.Scatter(
            x=sell_dates, y=sell_prices,
            mode='markers', name='Sell (Trendline Break)',
            marker=dict(symbol='triangle-down', size=12, color='red', line=dict(width=1, color='darkred'))
        ))

    fig.update_layout(
        title=f"📈 {ticker} Trendline Breakdown + ATR Position Sizing",
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
        st.subheader("🔍 과거 차트 복기 + ATR 포지션 사이징")
        st.info("💡 추세선 브레이크다운 + ATR 변동성 기반 비중 관리")
        
        col_sel, col_blank = st.columns([1, 3])
        with col_sel:
            selected_ticker = st.selectbox(
                "분석할 종목 선택", 
                ['TQQQ', 'NVDA', 'TSLA', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'QQQ', 'XLK']
            )
        
        if selected_ticker:
            # 계좌 크기 입력
            account_size = st.number_input(
                "💰 계좌 크기 (USD)", 
                min_value=10000, 
                max_value=10000000, 
                value=100000, 
                step=10000,
                help="ATR 기반 포지션 사이징 계산에 사용됩니다"
            )
            
            with st.spinner(f"{selected_ticker} 데이터 분석 중..."):
                hist_df, buys, sells, positions = run_technical_backtest(selected_ticker, account_size=account_size)
                
                if hist_df is not None:
                    fig = plot_backtest_chart(selected_ticker, hist_df, buys, sells)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 통계 표시
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("🟢 매수 신호", f"{len(buys)}회")
                    with col2:
                        st.metric("🔴 손절 신호", f"{len(sells)}회")
                    with col3:
                        if positions:
                            avg_position = sum(p['position_pct'] for p in positions) / len(positions)
                            st.metric("📊 평균 비중", f"{avg_position:.1f}%")
                    
                    # ATR 기반 포지션 사이징 정보
                    if positions:
                        st.markdown("---")
                        st.subheader("📊 ATR 기반 포지션 사이징")
                        st.info("💡 변동성이 높을수록 비중을 낮춰 리스크를 관리합니다")
                        
                        # 최근 3개 신호만 표시
                        recent_positions = positions[-3:] if len(positions) > 3 else positions
                        
                        for pos in recent_positions:
                            st.markdown(f"""
                            <div style='background:#f8f9fa; padding:12px; border-radius:8px; margin:8px 0; border-left:4px solid #28a745;'>
                                <div style='display:flex; justify-content:space-between; align-items:center;'>
                                    <div>
                                        <b>📅 {pos['date'].strftime('%Y-%m-%d')}</b> | 
                                        가격: ${pos['price']:.2f} | 
                                        ATR: ${pos['atr']:.2f}
                                    </div>
                                    <div style='text-align:right;'>
                                        <div style='font-size:1.2em; color:#28a745; font-weight:bold;'>
                                            {pos['shares']:,}주 ({pos['position_pct']:.1f}%)
                                        </div>
                                        <div style='font-size:0.9em; color:#666;'>
                                            ${pos['position_value']:,.0f}
                                        </div>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <p style='text-align: center; color: gray; font-size: 0.8em; margin-top: 20px;'>
                        * 추세선 브레이크다운 + ATR 포지션 사이징: 계좌 1.5% 리스크 기준
                    </p>
                    """, unsafe_allow_html=True)
                else:
                    st.warning("데이터를 불러올 수 없습니다.")

if __name__ == "__main__":
    main()