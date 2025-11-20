"""
M7 Bot - Streamlit Dashboard
SaaS MVP for Signal Visualization with Enhanced Error Handling and Type Safety
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import DB Manager
from m7_cloud import DBManager

# ============================================================================
# PAGE CONFIGURATION
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
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_signals_data(limit: int = 100) -> pd.DataFrame:
    """
    Supabase에서 신호 데이터 로드
    
    Args:
        limit (int): 조회할 최대 데이터 개수 (기본값: 100)
    
    Returns:
        pd.DataFrame: 신호 데이터프레임. 실패 시 빈 DataFrame 반환
    
    Raises:
        None: 모든 예외는 내부에서 처리되며 사용자 친화적 메시지 표시
    """
    try:
        # .env 파일이 우선, Streamlit Cloud에서는 st.secrets 사용
        try:
            if 'SUPABASE_URL' in st.secrets:
                os.environ['SUPABASE_URL'] = st.secrets['SUPABASE_URL']
                os.environ['SUPABASE_KEY'] = st.secrets['SUPABASE_KEY']
        except Exception:
            # st.secrets 없으면 .env 파일 사용 (이미 load_dotenv()로 로드됨)
            pass
        
        db = DBManager()
        response = db.supabase.table("m7_signals").select("*").order("created_at", desc=True).limit(limit).execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            # 날짜 형식 변환
            df['created_at'] = pd.to_datetime(df['created_at'])
            return df
        else:
            st.warning("⚠️ 데이터베이스에 저장된 신호가 없습니다.")
            return pd.DataFrame()
            
    except ConnectionError:
        st.error("❌ 인터넷 연결을 확인해주세요. 데이터를 불러올 수 없습니다.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ 데이터를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.\n\n상세 오류: {str(e)}")
        return pd.DataFrame()


def calculate_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    대시보드 메트릭 계산
    
    Args:
        df (pd.DataFrame): 신호 데이터프레임
    
    Returns:
        Dict[str, Any]: 계산된 메트릭 딕셔너리
            - total_signals (int): 총 신호 수
            - recent_stocks (List[str]): 최근 포착 종목 리스트
            - strong_buy_count (int): 강력 매수 신호 수
            - today_signals (int): 오늘 생성된 신호 수
    """
    if df.empty:
        return {
            'total_signals': 0,
            'recent_stocks': [],
            'strong_buy_count': 0,
            'today_signals': 0
        }
    
    # 총 신호 수
    total_signals = len(df)
    
    # 최근 포착 종목 (중복 제거)
    recent_stocks = df['ticker'].unique()[:10].tolist()
    
    # 강력 매수 신호 수
    strong_buy_count = len(df[df['signal_type'].str.contains('STRONG BUY|강력 매수', case=False, na=False)])
    
    # 오늘 신호 수
    today = datetime.now().date()
    today_signals = len(df[df['created_at'].dt.date == today])
    
    return {
        'total_signals': total_signals,
        'recent_stocks': recent_stocks,
        'strong_buy_count': strong_buy_count,
        'today_signals': today_signals
    }


def get_filter_stats(df: pd.DataFrame) -> Dict[str, float]:
    """
    필터 통과율 계산
    
    Args:
        df (pd.DataFrame): 신호 데이터프레임
    
    Returns:
        Dict[str, float]: 필터별 통과율 (0-100%)
            - market: 거시경제 필터 통과율
            - chart: 차트 기술 필터 통과율
            - news: 뉴스 감성 필터 통과율
            - options: 옵션 데이터 필터 통과율
            - support: 지지/저항선 필터 통과율
    """
    if df.empty or 'filters' not in df.columns:
        return {}
    
    filter_stats: Dict[str, float] = {}
    filter_names = ['market', 'chart', 'news', 'options', 'support']
    
    for filter_name in filter_names:
        try:
            pass_count = sum(df['filters'].apply(lambda x: x.get(filter_name) == 'pass' if isinstance(x, dict) else False))
            total_count = len(df)
            pass_rate = (pass_count / total_count * 100) if total_count > 0 else 0
            filter_stats[filter_name] = pass_rate
        except Exception:
            filter_stats[filter_name] = 0.0
    
    return filter_stats


# ============================================================================
# ⚠️ LEGAL DISCLAIMER (법적 면책 조항) - MUST BE VISIBLE
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
# MAIN DASHBOARD
# ============================================================================
def main() -> None:
    """
    메인 대시보드 함수
    
    Streamlit 대시보드의 전체 UI를 렌더링하고 데이터를 표시합니다.
    사용자 인터랙션을 처리하고 실시간 데이터를 시각화합니다.
    
    Returns:
        None
    """
    # Header
    st.title("🚀 M7 Bot Dashboard")
    
    # ✅ [추가] 면책 조항 배너 표시
    st.markdown(DISCLAIMER_HTML, unsafe_allow_html=True)
    
    st.markdown("**SaaS Cloud Version (V2.1)** - Real-time Signal Monitoring")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ 설정")
        
        # 데이터 새로고침 버튼
        if st.button("🔄 데이터 새로고침", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        
        # 필터 옵션
        st.subheader("📊 필터 옵션")
        data_limit = st.slider("표시할 신호 개수", 10, 200, 100, 10)
        
        show_filters = st.multiselect(
            "신호 유형 필터",
            ["강력 매수", "관망", "매수 금지", "악재 차단", "매도"],
            default=["강력 매수"]
        )
        
        st.markdown("---")
        st.markdown("### 📌 정보")
        st.info("""
        **데이터 소스**: Supabase Cloud DB
        
        **업데이트**: GitHub Actions (매일 23:30 KST)
        
        **5중 필터**:
        1. 거시경제
        2. 차트 기술
        3. 뉴스 감성
        4. 옵션 데이터
        5. 지지/저항선
        """)
    
    # Load Data with spinner
    with st.spinner("📡 시장 데이터를 분석 중입니다..."):
        df = load_signals_data(limit=data_limit)
    
    if df.empty:
        st.warning("⚠️ 표시할 데이터가 없습니다.")
        st.info("💡 GitHub Actions가 실행되면 데이터가 표시됩니다.")
        return
    
    # Calculate Metrics
    try:
        metrics = calculate_metrics(df)
        filter_stats = get_filter_stats(df)
    except Exception as e:
        st.error(f"❌ 메트릭 계산 중 오류가 발생했습니다: {str(e)}")
        return
    
    # ========================================================================
    # METRICS ROW
    # ========================================================================
    st.subheader("📊 요약 지표")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="총 신호 수",
            value=f"{metrics['total_signals']:,}",
            delta=f"+{metrics['today_signals']} 오늘"
        )
    
    with col2:
        st.metric(
            label="강력 매수 신호",
            value=f"{metrics['strong_buy_count']:,}",
            delta=f"{metrics['strong_buy_count']/metrics['total_signals']*100:.1f}%" if metrics['total_signals'] > 0 else "0%"
        )
    
    with col3:
        st.metric(
            label="분석 종목 수",
            value=f"{len(metrics['recent_stocks'])}",
            delta="M7 Stocks"
        )
    
    with col4:
        # 최근 신호 시간
        if not df.empty:
            try:
                latest_time = df['created_at'].max()
                # timezone-aware datetime으로 변환
                if latest_time.tzinfo is None:
                    latest_time = latest_time.replace(tzinfo=pd.Timestamp.now().tzinfo)
                
                current_time = pd.Timestamp.now(tz=latest_time.tzinfo) if latest_time.tzinfo else pd.Timestamp.now()
                hours_ago = (current_time - latest_time).total_seconds() / 3600
                
                st.metric(
                    label="최근 신호",
                    value=f"{hours_ago:.1f}시간 전",
                    delta=latest_time.strftime("%m/%d %H:%M")
                )
            except Exception:
                st.metric(label="최근 신호", value="N/A")
    
    st.markdown("---")
    
    # ========================================================================
    # FILTER STATISTICS
    # ========================================================================
    if filter_stats:
        st.subheader("🔍 필터 통과율")
        
        filter_cols = st.columns(5)
        filter_names_kr = {
            'market': '거시경제',
            'chart': '차트',
            'news': '뉴스',
            'options': '옵션',
            'support': '지지선'
        }
        
        for idx, (filter_name, pass_rate) in enumerate(filter_stats.items()):
            with filter_cols[idx]:
                st.metric(
                    label=filter_names_kr.get(filter_name, filter_name),
                    value=f"{pass_rate:.1f}%",
                    delta="통과율"
                )
        
        st.markdown("---")
    
    # ========================================================================
    # RECENT STOCKS
    # ========================================================================
    st.subheader("📈 최근 포착 종목")
    
    if metrics['recent_stocks']:
        # 종목을 버튼 형태로 표시
        stock_cols = st.columns(min(len(metrics['recent_stocks']), 7))
        for idx, stock in enumerate(metrics['recent_stocks'][:7]):
            with stock_cols[idx]:
                stock_count = len(df[df['ticker'] == stock])
                st.button(f"**{stock}** ({stock_count})", use_container_width=True)
    
    st.markdown("---")
    
    # ========================================================================
    # DATA TABLE
    # ========================================================================
    st.subheader("📋 신호 내역")
    
    # 필터 적용
    try:
        if show_filters:
            filter_pattern = '|'.join(show_filters)
            filtered_df = df[df['signal_type'].str.contains(filter_pattern, case=False, na=False)]
        else:
            filtered_df = df
    except Exception as e:
        st.error(f"❌ 필터 적용 중 오류 발생: {str(e)}")
        filtered_df = df
    
    if filtered_df.empty:
        st.info("선택한 필터에 해당하는 신호가 없습니다.")
    else:
        try:
            # 표시할 컬럼 선택
            display_columns = ['created_at', 'ticker', 'signal_type', 'entry_price']
            
            # 데이터프레임 스타일링
            styled_df = filtered_df[display_columns].copy()
            styled_df.columns = ['생성일시', '종목', '신호', '진입가']
            
            # 날짜 형식 변경
            styled_df['생성일시'] = styled_df['생성일시'].dt.strftime('%Y-%m-%d %H:%M')
            
            # 가격 형식 변경
            styled_df['진입가'] = styled_df['진입가'].apply(lambda x: f"${x:.2f}")
            
            # 테이블 표시
            st.dataframe(
                styled_df,
                use_container_width=True,
                height=400,
                hide_index=True
            )
            
            # 다운로드 버튼
            csv = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 CSV 다운로드",
                data=csv,
                file_name=f"m7_signals_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        except Exception as e:
            st.error(f"❌ 테이블 표시 중 오류 발생: {str(e)}")
    
    # ========================================================================
    # DETAILED VIEW (Expandable)
    # ========================================================================
    with st.expander("🔍 상세 필터 정보 보기"):
        if not filtered_df.empty:
            try:
                selected_idx = st.selectbox(
                    "신호 선택",
                    range(len(filtered_df)),
                    format_func=lambda x: f"{filtered_df.iloc[x]['ticker']} - {filtered_df.iloc[x]['created_at'].strftime('%Y-%m-%d %H:%M')}"
                )
                
                if selected_idx is not None:
                    selected_signal = filtered_df.iloc[selected_idx]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("### 기본 정보")
                        st.write(f"**종목**: {selected_signal['ticker']}")
                        st.write(f"**신호**: {selected_signal['signal_type']}")
                        st.write(f"**진입가**: ${selected_signal['entry_price']:.2f}")
                        st.write(f"**생성일시**: {selected_signal['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    with col2:
                        st.markdown("### 필터 결과")
                        if isinstance(selected_signal['filters'], dict):
                            for filter_name, result in selected_signal['filters'].items():
                                emoji = "✅" if result == "pass" else "❌"
                                st.write(f"{emoji} **{filter_name}**: {result}")
                        else:
                            st.write("필터 정보 없음")
            except Exception as e:
                st.error(f"❌ 상세 정보 표시 중 오류 발생: {str(e)}")
    
    # Footer
    st.markdown("---")
    st.markdown(
        f"<div style='text-align: center; color: gray;'>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        f"M7 Bot V2 (Cloud) | Powered by Supabase & Streamlit</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
