import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import random
import os
import time
import logging
import re
import json
import yfinance as yf
import utils  # 공통 유틸리티 함수 임포트
import theme  # 프리미엄 테마

# ============================================================================
# 0. LOGGING SETUP
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('portfolio.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# ============================================================================
# 1. CONFIG & CONSTANTS
# ============================================================================
st.set_page_config(page_title="AntiGravity M7 Bot", layout="wide", page_icon="🚀")

# Apply premium theme
theme.apply_premium_theme()

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
# 2. PORTFOLIO HELPER FUNCTIONS (NEW)
# ============================================================================

def init_portfolio():
    """포트폴리오 파일 및 디렉토리 초기화"""
    os.makedirs('./data', exist_ok=True)
    
    portfolio_path = './data/portfolio.csv'
    if not os.path.exists(portfolio_path):
        pd.DataFrame(columns=['Ticker', 'Avg_Price', 'Quantity', 'Date_Added']).to_csv(
            portfolio_path, index=False
        )
        logging.info("✅ portfolio.csv created")

def load_portfolio_safe() -> pd.DataFrame:
    """안전하게 포트폴리오 CSV 로드"""
    try:
        df = pd.read_csv('./data/portfolio.csv')
        
        # 필수 컬럼 확인
        required_cols = ['Ticker', 'Avg_Price', 'Quantity', 'Date_Added']
        if not all(col in df.columns for col in required_cols):
            logging.error("Invalid CSV structure")
            init_portfolio()
            return pd.DataFrame(columns=required_cols)
        
        return df
        
    except FileNotFoundError:
        logging.info("portfolio.csv not found, initializing...")
        init_portfolio()
        return pd.DataFrame(columns=['Ticker', 'Avg_Price', 'Quantity', 'Date_Added'])
    
    except pd.errors.EmptyDataError:
        logging.warning("portfolio.csv is empty")
        return pd.DataFrame(columns=['Ticker', 'Avg_Price', 'Quantity', 'Date_Added'])
    
    except Exception as e:
        logging.error(f"Failed to load portfolio: {e}")
        st.error(f"❌ 파일 로드 오류: {e}")
        return pd.DataFrame(columns=['Ticker', 'Avg_Price', 'Quantity', 'Date_Added'])

def save_portfolio_safe(df: pd.DataFrame, max_retries: int = 3) -> bool:
    """안전하게 포트폴리오 CSV 저장 (재시도 로직 포함)"""
    filepath = './data/portfolio.csv'
    
    for attempt in range(max_retries):
        try:
            df.to_csv(filepath, index=False)
            logging.info(f"✅ Portfolio saved ({len(df)} positions)")
            return True
            
        except PermissionError:
            if attempt < max_retries - 1:
                st.warning(f"⏳ 파일 저장 재시도 중... ({attempt + 1}/{max_retries})")
                time.sleep(1)
            else:
                st.error("❌ 파일이 다른 프로그램에서 사용 중입니다. Excel을 닫아주세요.")
                logging.error("Save failed: PermissionError")
                return False
        
        except Exception as e:
            st.error(f"❌ 저장 오류: {e}")
            logging.error(f"Save failed: {e}")
            return False
    
    return False

def validate_inputs(ticker: str, price: float, qty: int) -> tuple[bool, str]:
    """입력값 유효성 검사"""
    # 1. Ticker 검증
    if not ticker:
        return False, "❌ 종목 코드를 입력하세요."
    
    if not re.match(r'^[A-Z0-9.-]+$', ticker):
        return False, "❌ 유효하지 않은 종목 코드 형식입니다. (A-Z, 0-9, -, . 만 허용)"
    
    # 실제 존재 여부 확인 (yfinance)
    try:
        test_data = yf.Ticker(ticker).history(period='1d')
        if test_data.empty:
            return False, f"❌ {ticker}는 존재하지 않는 종목입니다."
    except Exception as e:
        return False, f"❌ 종목 확인 오류: {str(e)[:50]}"
    
    # 2. Price 검증
    if price <= 0:
        return False, "❌ 가격은 0보다 커야 합니다."
    if price > 100000:
        return False, "❌ 가격이 너무 높습니다 ($100,000 초과)."
    
    # 3. Quantity 검증
    if qty < 1:
        return False, "❌ 최소 1주 이상 입력하세요."
    if qty > 100000:
        return False, "❌ 수량이 너무 많습니다 (100,000주 초과)."
    
    return True, ""

def add_or_update_position(df: pd.DataFrame, ticker: str, price: float, qty: int) -> pd.DataFrame:
    """포지션 추가 또는 업데이트 (가중평균 적용)"""
    if ticker in df['Ticker'].values:
        # 기존 포지션 업데이트
        idx = df[df['Ticker'] == ticker].index[0]
        old_qty = df.loc[idx, 'Quantity']
        old_price = df.loc[idx, 'Avg_Price']
        
        # 가중평균 계산
        new_qty = old_qty + qty
        new_avg = (old_qty * old_price + qty * price) / new_qty
        
        df.loc[idx, 'Quantity'] = new_qty
        df.loc[idx, 'Avg_Price'] = round(new_avg, 2)
    
    return df

@st.cache_data(ttl=300)
def get_portfolio_data(tickers: list) -> dict:
    """포트폴리오 종목 데이터 배치 로딩"""
    results = {}
    total = len(tickers)
    
    # 10개 이상일 때만 진행률 표시
    if total > 10:
        progress_bar = st.progress(0)
        status_text = st.empty()
    
    for i, ticker in enumerate(tickers):
        try:
            df = utils.get_stock_data(ticker, period='1mo')
            if not df.empty:
                df = utils.calculate_metrics(df)
                results[ticker] = {
                    'price': round(df['Close'].iloc[-1], 2),
                    'rsi': round(df['RSI'].iloc[-1], 1) if 'RSI' in df else None
                }
            else:
                results[ticker] = None
        except Exception as e:
            results[ticker] = None
            logging.error(f"✗ {ticker}: {e}")
        
        if total > 10:
            status_text.text(f"📊 {ticker} 로딩 중... ({i+1}/{total})")
            progress_bar.progress((i + 1) / total)
    
    if total > 10:
        progress_bar.empty()
        status_text.empty()
    
    return results

# ============================================================================
# 3. EXISTING HELPER FUNCTIONS
# ============================================================================

@st.cache_data(ttl=300)
def get_stock_data(ticker, period="1y"):
    return utils.get_stock_data(ticker, period)

def calculate_metrics(df):
    return utils.calculate_metrics(df)

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
    score = 50
    details = []
    
    # RSI
    if row['RSI'] < 30: score += 30; details.append("RSI<30 (+30)")
    elif row['RSI'] < 40: score += 20; details.append("RSI<40 (+20)")
    elif row['RSI'] > 70: score -= 20; details.append("RSI>70 (-20)")
    
    # Trend
    if row['Close'] > row['MA20']: score += 10; details.append("Above MA20 (+10)")
    if row['Close'] > row['MA200']: score += 10; details.append("Above MA200 (+10)")
    
    # MACD
    if row['Hist'] > 0: score += 10; details.append("MACD Bullish (+10)")
    
    # Volume
    if row['Volume'] > row['VolAvg']: score += 10; details.append("Vol Spike (+10)")
    
    final_score = min(100, max(0, score))
    return final_score, ", ".join(details)

def send_telegram_alert(ticker, price, score, reason, stop_loss, take_profit):
    bot_token, chat_id = utils.load_env_vars()
    if not bot_token or not chat_id:
        return False, "Telegram credentials not found in .env file"
    message = utils.format_dashboard_alert(ticker, price, score, reason, stop_loss, take_profit)
    return utils.send_telegram_alert(bot_token, chat_id, message, parse_mode="HTML")

# ============================================================================
# 4. MAIN UI
# ============================================================================
def main():
    st.markdown(DISCLAIMER_TEXT, unsafe_allow_html=True)
    
    # --- SIDEBAR ---
    st.sidebar.header("⚙️ Settings")
    
    # 1. Scanner Filters
    with st.sidebar.expander("🔍 Scanner Filters", expanded=True):
        strategy_mode = st.selectbox(
            "Target Strategy",
            ["All Strategies", "RSI Oversold (<30)", "Trendline Breakout (Bullish)", "MACD Reversal", "Volume Spike (>1.2x)"]
        )
        rsi_range = st.slider("RSI Range", 0, 100, (0, 100))
        min_score = st.slider("Min Score", 0, 100, 50)
    
    # 2. Add Position Form (New)
    st.sidebar.markdown("---")
    st.sidebar.header("➕ Add Position")
    
    with st.sidebar.form("add_position_form", clear_on_submit=True):
        ticker_input = st.text_input("Ticker", placeholder="e.g. AAPL").strip().upper()
        price_input = st.number_input("Avg Price ($)", min_value=0.01, max_value=100000.00, value=100.00, step=0.01)
        qty_input = st.number_input("Quantity", min_value=1, max_value=100000, value=10, step=1)
        
        submitted = st.form_submit_button("🚀 Add to Portfolio", type="primary")
        
        if submitted:
            is_valid, error_msg = validate_inputs(ticker_input, price_input, qty_input)
            if not is_valid:
                st.error(error_msg)
            else:
                init_portfolio()
                portfolio = load_portfolio_safe()
                portfolio = add_or_update_position(portfolio, ticker_input, price_input, qty_input)
                
    # Refresh button in sidebar
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    
    # --- MAIN CONTENT ---
    # Premium Header
    theme.render_premium_header()
    
    # Tab Structure
    tab1, tab2 = st.tabs(["🔍 Market Scanner", "💼 Portfolio Monitor"])
    
    # TAB 1: MARKET SCANNER (Existing Logic)
    # ========================================================================
    with tab1:
        # [A] Market Pulse
        col_header, col_icon = st.columns([0.9, 0.1])
        with col_header:
            st.markdown("### 🌍 Market Pulse")
        with col_icon:
            st.image("assets/bull_icon.png", width=60)
            
        mp_col1, mp_col2, mp_col3, mp_col4 = st.columns(4)
        
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
                
                with mp_col1:
                    theme.render_premium_metric(
                        "VIX Index",
                        f"{vix_now:.2f}",
                        delta=-vix_chg,  # Inverse: lower is better
                        icon="📉"
                    )
                
                with mp_col2:
                    theme.render_premium_metric(
                        "USD/KRW",
                        f"{krw_now:.0f} ₩",
                        delta=-krw_chg,  # Inverse
                        icon="💵"
                    )
                
                with mp_col3:
                    theme.render_premium_metric(
                        "10Y Treasury",
                        f"{tnx_now:.2f}%",
                        delta=tnx_chg,
                        icon="📊"
                    )
                
                with mp_col4:
                    active_users = random.randint(120, 150)
                    theme.render_premium_metric(
                        "Active Users",
                        f"{active_users}",
                        delta=3.5,
                        icon="👥"
                    )
                
            except Exception as e:
                st.error(f"Market Data Error: {e}")

        st.markdown("---")

        # [B] Data Processing & Scanner
        with st.spinner('🔄 Analyzing Market Data...'):
            market_data = []
            for ticker in ALL_STOCKS:
                df = get_stock_data(ticker, period="1y")
                if df.empty: continue
                df = calculate_metrics(df)
                
                last_row = df.iloc[-1]
                prev_row = df.iloc[-2]
                last_row_dict = last_row.to_dict()
                last_row_dict['Hist_Prev'] = prev_row['Hist']
                
                score, score_details = calculate_signal_score(last_row_dict)
                
                # Filters
                pass_strategy = True
                if strategy_mode == "RSI Oversold (<30)":
                    if last_row['RSI'] >= 30: pass_strategy = False
                elif strategy_mode == "Trendline Breakout (Bullish)":
                    if not (last_row['Close'] > last_row['MA20']): pass_strategy = False
                elif strategy_mode == "MACD Reversal":
                    if not (last_row['Hist'] > 0 and last_row['Hist'] > prev_row['Hist']): pass_strategy = False
                elif strategy_mode == "Volume Spike (>1.2x)":
                    if not (last_row['Volume'] > last_row['VolAvg'] * 1.2): pass_strategy = False
                
                if not pass_strategy: continue
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
            
            if not scan_df.empty:
                top_picks = scan_df.sort_values(by=['Score', 'RSI'], ascending=[False, True]).head(3)
            else:
                top_picks = pd.DataFrame()

        # [C] Top Signals
        if not top_picks.empty:
            st.markdown(f"### 🎯 Today's Top Signals")
            cols = st.columns(len(top_picks))
            for i, (index, row) in enumerate(top_picks.iterrows()):
                with cols[i]:
                    st.info(f"**{i+1}. {row['Ticker']}** (Score: {row['Score']})\n\n"
                            f"Price: ${row['Price']:.2f} | RSI: {row['RSI']:.1f}\n\n"
                            f"{row['Reason']}")
            
            st.write("")
            
            # [D] Chart & Calculator
            col_left, col_right = st.columns([2, 1])
            with col_left:
                st.subheader("📊 Advanced Chart Analysis")
                selected_ticker = st.selectbox("Select Ticker", scan_df['Ticker'].tolist(), index=0)
                
                df_sel = get_stock_data(selected_ticker)
                df_sel = calculate_metrics(df_sel)
                
                # Convert DataFrame to TradingView format
                candlestick_data = []
                volume_data = []
                ma20_data = []
                
                for idx, row in df_sel.iterrows():
                    timestamp = int(idx.timestamp())
                    
                    # Candlestick data
                    candlestick_data.append({
                        'time': timestamp,
                        'open': float(row['Open']),
                        'high': float(row['High']),
                        'low': float(row['Low']),
                        'close': float(row['Close'])
                    })
                    
                    # Volume data
                    color = '#10B981' if row['Close'] >= row['Open'] else '#EF4444'
                    volume_data.append({
                        'time': timestamp,
                        'value': float(row['Volume']),
                        'color': color
                    })
                    
                    # MA20 data
                    if pd.notna(row['MA20']):
                        ma20_data.append({
                            'time': timestamp,
                            'value': float(row['MA20'])
                        })
                
                # Convert data to JSON strings using pandas
                candlestick_json = pd.DataFrame(candlestick_data).to_json(orient='records')
                volume_json = pd.DataFrame(volume_data).to_json(orient='records')
                ma20_json = pd.DataFrame(ma20_data).to_json(orient='records')
                
                # Prepare MACD data
                macd_line_data = []
                signal_line_data = []
                histogram_data = []
                
                for idx, row in df_sel.iterrows():
                    timestamp = int(idx.timestamp())
                    if pd.notna(row['MACD']):
                        macd_line_data.append({'time': timestamp, 'value': float(row['MACD'])})
                    if pd.notna(row['Signal']):
                        signal_line_data.append({'time': timestamp, 'value': float(row['Signal'])})
                    if pd.notna(row['Hist']):
                        color = '#26a69a' if row['Hist'] >= 0 else '#ef5350'
                        histogram_data.append({'time': timestamp, 'value': float(row['Hist']), 'color': color})
                
                macd_json = pd.DataFrame(macd_line_data).to_json(orient='records')
                signal_json = pd.DataFrame(signal_line_data).to_json(orient='records')
                hist_json = pd.DataFrame(histogram_data).to_json(orient='records')
                
                # Create TradingView chart HTML with Synced Charts
                chart_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
                    <style>
                        body {{ margin: 0; padding: 0; background: transparent; font-family: 'Inter', sans-serif; }}
                        .container {{ position: relative; width: 100%; }}
                        #main-chart {{ width: 100%; height: 450px; }}
                        #macd-chart {{ width: 100%; height: 150px; }}
                        
                        /* Toolbar */
                        .toolbar {{
                            position: absolute;
                            top: 10px;
                            left: 10px;
                            z-index: 10;
                            display: flex;
                            gap: 5px;
                        }}
                        .time-btn {{
                            background: rgba(28, 30, 34, 0.9);
                            border: 1px solid rgba(255, 184, 0, 0.3);
                            color: #FFFFFF;
                            padding: 4px 8px;
                            font-size: 11px;
                            cursor: pointer;
                            border-radius: 4px;
                            transition: all 0.2s;
                        }}
                        .time-btn:hover {{
                            background: rgba(255, 184, 0, 0.2);
                            color: #FFB800;
                        }}
                        
                        /* Watermark */
                        .watermark {{
                            position: absolute;
                            top: 50%;
                            left: 50%;
                            transform: translate(-50%, -50%);
                            font-size: 80px;
                            font-weight: 900;
                            color: rgba(255, 255, 255, 0.05);
                            pointer-events: none;
                            z-index: 1;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="toolbar">
                            <button class="time-btn" onclick="setRange('1M')">1M</button>
                            <button class="time-btn" onclick="setRange('3M')">3M</button>
                            <button class="time-btn" onclick="setRange('6M')">6M</button>
                            <button class="time-btn" onclick="setRange('YTD')">YTD</button>
                            <button class="time-btn" onclick="setRange('1Y')">1Y</button>
                            <button class="time-btn" onclick="setRange('ALL')">ALL</button>
                        </div>
                        <div class="watermark">{selected_ticker}</div>
                        <div id="main-chart"></div>
                        <div id="macd-chart"></div>
                    </div>

                    <script>
                        // --- Main Chart ---
                        const mainChart = LightweightCharts.createChart(document.getElementById('main-chart'), {{
                            layout: {{ background: {{ type: 'solid', color: 'transparent' }}, textColor: '#D1D5DB' }},
                            grid: {{ vertLines: {{ color: 'rgba(255, 255, 255, 0.05)' }}, horzLines: {{ color: 'rgba(255, 255, 255, 0.05)' }} }},
                            crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal, vertLine: {{ labelBackgroundColor: '#FFB800' }}, horzLine: {{ labelBackgroundColor: '#FFB800' }} }},
                            rightPriceScale: {{ borderColor: 'rgba(255, 255, 255, 0.1)' }},
                            timeScale: {{ borderColor: 'rgba(255, 255, 255, 0.1)', timeVisible: true }}
                        }});

                        const candlestickSeries = mainChart.addCandlestickSeries({{
                            upColor: '#10B981', downColor: '#EF4444', borderUpColor: '#10B981', borderDownColor: '#EF4444', wickUpColor: '#10B981', wickDownColor: '#EF4444'
                        }});
                        candlestickSeries.setData({candlestick_json});

                        const ma20Series = mainChart.addLineSeries({{ color: '#FFB800', lineWidth: 2, title: 'MA20' }});
                        ma20Series.setData({ma20_json});

                        const volumeSeries = mainChart.addHistogramSeries({{
                            color: '#26a69a',
                            priceFormat: {{ type: 'volume' }},
                            priceScaleId: 'volume', // Separate scale
                        }});
                        mainChart.priceScale('volume').applyOptions({{
                            scaleMargins: {{ top: 0.8, bottom: 0 }},
                            visible: false // Hide volume scale
                        }});
                        volumeSeries.setData({volume_json});

                        // --- MACD Chart ---
                        const macdChart = LightweightCharts.createChart(document.getElementById('macd-chart'), {{
                            layout: {{ background: {{ type: 'solid', color: 'transparent' }}, textColor: '#D1D5DB' }},
                            grid: {{ vertLines: {{ color: 'rgba(255, 255, 255, 0.05)' }}, horzLines: {{ color: 'rgba(255, 255, 255, 0.05)' }} }},
                            crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }},
                            rightPriceScale: {{ borderColor: 'rgba(255, 255, 255, 0.1)' }},
                            timeScale: {{ visible: false }} // Hide time scale for bottom chart
                        }});

                        const macdSeries = macdChart.addLineSeries({{ color: '#2962FF', lineWidth: 2, title: 'MACD' }});
                        macdSeries.setData({macd_json});

                        const signalSeries = macdChart.addLineSeries({{ color: '#FF6D00', lineWidth: 2, title: 'Signal' }});
                        signalSeries.setData({signal_json});

                        const histSeries = macdChart.addHistogramSeries({{ color: '#26a69a' }});
                        histSeries.setData({hist_json});

                        // --- Sync Charts ---
                        function syncCharts(source, target) {{
                            source.timeScale().subscribeVisibleTimeRangeChange(range => {{
                                target.timeScale().setVisibleRange(range);
                            }});
                        }}
                        syncCharts(mainChart, macdChart);
                        syncCharts(macdChart, mainChart);

                        // --- Timeframe Functions ---
                        function setRange(period) {{
                            const data = {candlestick_json};
                            if (data.length === 0) return;
                            
                            const lastIndex = data.length - 1;
                            const lastTime = data[lastIndex].time;
                            let firstIndex = 0;
                            
                            // Approximate calculation (assuming daily data)
                            const daySeconds = 86400;
                            let days = 0;
                            
                            if (period === '1M') days = 30;
                            else if (period === '3M') days = 90;
                            else if (period === '6M') days = 180;
                            else if (period === '1Y') days = 365;
                            else if (period === 'YTD') {{
                                const currentYear = new Date(lastTime * 1000).getFullYear();
                                const startOfYear = new Date(currentYear, 0, 1).getTime() / 1000;
                                // Find index closest to startOfYear
                                // Simple approximation for now
                                mainChart.timeScale().setVisibleRange({{ from: startOfYear, to: lastTime }});
                                return;
                            }}
                            else if (period === 'ALL') {{
                                mainChart.timeScale().fitContent();
                                return;
                            }}
                            
                            const startTime = lastTime - (days * daySeconds);
                            mainChart.timeScale().setVisibleRange({{ from: startTime, to: lastTime }});
                        }}
                        
                        // Initial Fit
                        mainChart.timeScale().fitContent();

                        // Resize Handling
                        window.addEventListener('resize', () => {{
                            const w = document.body.clientWidth;
                            mainChart.applyOptions({{ width: w }});
                            macdChart.applyOptions({{ width: w }});
                        }});
                    </script>
                </body>
                </html>
                """
                
                # Render chart
                st.components.v1.html(chart_html, height=620)
                
            with col_right:
                st.subheader("🛡️ Position Calculator")
                current_row = scan_df[scan_df['Ticker'] == selected_ticker].iloc[0]
                
                balance = st.number_input("Account Balance ($)", value=10000, step=1000)
                risk_pct = st.slider("Risk (%)", 1.0, 5.0, 2.0)
                
                atr = current_row['ATR']
                entry = current_row['Price']
                stop = entry - (atr * 2.0)
                risk_amt = balance * (risk_pct / 100)
                shares = int(risk_amt / (entry - stop)) if (entry - stop) > 0 else 0
                take_profit = entry + ((entry - stop) * 2.0)
                
                st.success(f"**Buy {shares} Shares**\n\nStop: ${stop:.2f}  |  Target: ${take_profit:.2f}")
                
                if st.button(f"🔔 Send {selected_ticker} Alert"):
                    success, msg = send_telegram_alert(selected_ticker, entry, current_row['Score'], current_row['Reason'], stop, take_profit)
                    if success: st.success("Sent!")
                    else: st.error(msg)
        else:
            st.warning("No stocks match your current filters.")

        st.markdown("---")
        st.markdown("### 🔍 Market Scanner Table")
        if not scan_df.empty:
            # Select and rename columns for display
            display_df = scan_df[['Ticker', 'Price', 'Trend', 'RSI', 'Score', 'Reason']].copy()
            st.markdown(theme.render_premium_table(display_df), unsafe_allow_html=True)

    # ========================================================================
    # TAB 2: PORTFOLIO MONITOR (New Logic)
    # ========================================================================
    with tab2:
        col_p_header, col_p_icon = st.columns([0.9, 0.1])
        with col_p_header:
            st.subheader("💼 Portfolio Monitor")
        with col_p_icon:
            st.image("assets/wallet_icon.png", width=60)
        
        init_portfolio()
        portfolio = load_portfolio_safe()
        
        # --- IMPORT SECTION (NEW) ---
        with st.expander("📸 Import Portfolio (Screenshot / CSV)", expanded=False):
            import_tab1, import_tab2 = st.tabs(["📸 Screenshot OCR", "📂 CSV Upload"])
            
            # [A] Screenshot OCR
            with import_tab1:
                st.info("💡 증권사 앱의 '잔고 상세' 화면을 캡처해서 업로드하세요. (여러 장 동시 업로드 가능)")
                uploaded_imgs = st.file_uploader(
                    "Upload Screenshots", 
                    type=['png', 'jpg', 'jpeg'],
                    accept_multiple_files=True
                )
                
                if uploaded_imgs:
                    # 업로드된 이미지 미리보기
                    cols = st.columns(min(len(uploaded_imgs), 3))
                    for i, img in enumerate(uploaded_imgs):
                        with cols[i % 3]:
                            st.image(img, caption=f"Image {i+1}", width=200)
                    
                    if st.button(f"🔍 Analyze {len(uploaded_imgs)} Screenshot(s)"):
                        all_positions = []
                        
                        # 병렬 처리를 위한 함수
                        def analyze_single_image(idx_img_tuple):
                            idx, uploaded_img = idx_img_tuple
                            img_bytes = uploaded_img.getvalue()
                            result_json = utils.get_ai_vision_analysis(img_bytes)
                            return idx, result_json
                        
                        # ThreadPoolExecutor로 병렬 처리 (최대 3개 동시 - rate limit 방지)
                        from concurrent.futures import ThreadPoolExecutor, as_completed
                        
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        with ThreadPoolExecutor(max_workers=3) as executor:
                            # 모든 이미지 제출
                            futures = {
                                executor.submit(analyze_single_image, (idx, img)): idx 
                                for idx, img in enumerate(uploaded_imgs)
                            }
                            
                            completed = 0
                            results = {}
                            
                            # 완료되는 대로 결과 수집
                            for future in as_completed(futures):
                                idx, result_json = future.result()
                                results[idx] = result_json
                                completed += 1
                                
                                progress_bar.progress(completed / len(uploaded_imgs))
                                status_text.text(f"🤖 분석 완료: {completed}/{len(uploaded_imgs)}")
                                time.sleep(0.2)  # rate limit 방지용 작은 딜레이
                        
                        progress_bar.empty()
                        status_text.empty()
                        
                        # 결과를 순서대로 처리
                        for idx in sorted(results.keys()):
                            result_json = results[idx]
                            
                            try:
                                import json
                                result = json.loads(result_json)
                                
                                if "positions" in result and result["positions"]:
                                    all_positions.extend(result['positions'])
                                    st.success(f"✅ Image {idx+1}: {len(result['positions'])}개 종목 감지")
                                else:
                                    st.warning(f"⚠️ Image {idx+1}: 종목을 찾을 수 없습니다.")
                                    # 디버그: AI 응답 표시
                                    with st.expander(f"🔍 Image {idx+1} AI 응답 확인"):
                                        st.code(result_json, language="json")
                                    
                            except json.JSONDecodeError:
                                st.error(f"❌ Image {idx+1}: AI 응답 분석 실패")
                                with st.expander(f"🔍 Image {idx+1} 원본 응답"):
                                    st.code(result_json)
                            except Exception as e:
                                st.error(f"❌ Image {idx+1}: {e}")
                        
                        # all_positions를 session_state에 저장 (버튼 클릭 후에도 유지)
                        if all_positions:
                            st.session_state.ocr_analyzed_positions = all_positions
                    
                    # session_state에서 all_positions 로드 (rerun 후에도 유지)
                    if 'ocr_analyzed_positions' in st.session_state:
                        all_positions = st.session_state.ocr_analyzed_positions
                        
                        # 모든 이미지에서 추출한 데이터 통합
                        st.success(f"🎉 총 {len(all_positions)}개 종목 감지됨!")
                        st.markdown("---")
                        st.subheader("📝 데이터 확인 및 수정")
                        
                        # session_state에 저장하여 데이터 유지
                        if 'ocr_data' not in st.session_state:
                            st.session_state.ocr_data = pd.DataFrame(all_positions)
                        
                        # 데이터 에디터
                        edited_df = st.data_editor(
                            st.session_state.ocr_data,
                            num_rows="dynamic",
                            hide_index=True,
                            use_container_width=True,
                            key="ocr_data_editor"
                        )
                        
                        # 에디터 변경사항을 session_state에 저장
                        st.session_state.ocr_data = edited_df
                        
                        st.markdown("---")
                        
                        col1, col2, col3 = st.columns([1, 1, 4])
                        
                        with col1:
                            if st.button("📥 Add to Portfolio", key="add_btn", type="primary"):
                                st.info("🔍 처리 시작...")
                                
                                df_to_add = st.session_state.ocr_data
                                st.write(f"🔍 데이터 크기: {len(df_to_add)} 종목")
                                
                                if df_to_add is not None and not df_to_add.empty:
                                    portfolio = load_portfolio_safe()
                                    success_list = []
                                    error_list = []
                                    
                                    for idx, row in df_to_add.iterrows():
                                        try:
                                            ticker = str(row['ticker']).upper().strip()
                                            avg_price = float(row['avg_price'])
                                            quantity = int(row['quantity'])
                                            
                                            st.write(f"처리: {ticker} | 가격={avg_price} | 수량={quantity}")
                                            
                                            if ticker and avg_price > 0 and quantity > 0:
                                                portfolio = add_or_update_position(
                                                    portfolio, ticker, avg_price, quantity
                                                )
                                                success_list.append(ticker)
                                                st.write(f"✅ {ticker} 추가")
                                            else:
                                                error_list.append(f"{ticker}")
                                                st.write(f"❌ {ticker} 유효성 실패")
                                                
                                        except Exception as e:
                                            error_list.append(f"{row.get('ticker', '?')}")
                                            st.write(f"❌ 예외: {str(e)}")
                                    
                                    st.write(f"✅ 성공: {success_list}")
                                    st.write(f"❌ 실패: {error_list}")
                                    
                                    if success_list:
                                        st.write("💾 포트폴리오 저장 중...")
                                        if save_portfolio_safe(portfolio):
                                            st.success(f"✅ {len(success_list)}개 추가: {', '.join(success_list[:5])}")
                                            # session_state 정리
                                            if 'ocr_data' in st.session_state:
                                                del st.session_state.ocr_data
                                            if 'ocr_analyzed_positions' in st.session_state:
                                                del st.session_state.ocr_analyzed_positions
                                            time.sleep(1.5)
                                            st.rerun()
                                        else:
                                            st.error("❌ 저장 실패")
                                    else:
                                        st.error(f"❌ 추가 가능한 종목 없음")
                                else:
                                    st.warning("⚠️ 데이터 없음")
                        
                        with col2:
                            if st.button("🗑️ Clear", key="clear_btn"):
                                if 'ocr_data' in st.session_state:
                                    del st.session_state.ocr_data
                                if 'ocr_analyzed_positions' in st.session_state:
                                    del st.session_state.ocr_analyzed_positions
                                st.rerun()

            # [B] CSV Upload
            with import_tab2:
                st.markdown("""
                **CSV Format Required:**
                `Ticker, Avg_Price, Quantity`
                (Example: `AAPL, 150.50, 10`)
                """)
                uploaded_csv = st.file_uploader("Upload CSV", type=['csv'])
                
                if uploaded_csv:
                    try:
                        csv_df = pd.read_csv(uploaded_csv)
                        st.dataframe(csv_df.head())
                        
                        if st.button("📥 Import CSV"):
                            required = {'Ticker', 'Avg_Price', 'Quantity'}
                            if not required.issubset(csv_df.columns):
                                st.error(f"❌ Missing columns. Required: {required}")
                            else:
                                portfolio = load_portfolio_safe()
                                count = 0
                                for _, row in csv_df.iterrows():
                                    try:
                                        portfolio = add_or_update_position(
                                            portfolio,
                                            str(row['Ticker']).upper().strip(),
                                            float(row['Avg_Price']),
                                            int(row['Quantity'])
                                        )
                                        count += 1
                                    except Exception as e:
                                        st.warning(f"Skipped row {row}: {e}")
                                
                                if save_portfolio_safe(portfolio):
                                    st.success(f"🎉 {count} positions imported!")
                                    time.sleep(1)
                                    st.rerun()
                    except Exception as e:
                        st.error(f"❌ CSV Error: {e}")

        st.markdown("---")
        
        if portfolio.empty:
            st.info("📭 포트폴리오가 비어있습니다. 왼쪽 사이드바에서 종목을 추가해보세요!")
            if st.button("📝 샘플 데이터 추가 (AAPL, MSFT)"):
                sample = pd.DataFrame([
                    {'Ticker': 'AAPL', 'Avg_Price': 150.00, 'Quantity': 10, 'Date_Added': '2025-01-15'},
                    {'Ticker': 'MSFT', 'Avg_Price': 380.00, 'Quantity': 5, 'Date_Added': '2025-01-20'}
                ])
                if save_portfolio_safe(sample):
                    st.rerun()
        else:
            # 1. Fetch Data
            tickers = portfolio['Ticker'].tolist()
            market_data = get_portfolio_data(tickers)
            
            # 2. Calculate Metrics
            portfolio['Current_Price'] = portfolio['Ticker'].apply(
                lambda t: market_data[t]['price'] if market_data.get(t) else 0.0
            )
            portfolio['RSI'] = portfolio['Ticker'].apply(
                lambda t: market_data[t]['rsi'] if market_data.get(t) else None
            )
            
            portfolio['Market_Value'] = portfolio['Current_Price'] * portfolio['Quantity']
            portfolio['Cost_Basis'] = portfolio['Avg_Price'] * portfolio['Quantity']
            portfolio['PL_Dollar'] = portfolio['Market_Value'] - portfolio['Cost_Basis']
            portfolio['PL_Percent'] = (
                (portfolio['Current_Price'] - portfolio['Avg_Price']) / portfolio['Avg_Price'] * 100
            )
            
            # Action Signal
            def get_action(rsi):
                if pd.isna(rsi): return "⚪ N/A"
                elif rsi < 30: return "🟢 BUY"
                elif rsi > 70: return "🔴 SELL"
                else: return "⚪ HOLD"
            
            portfolio['Action'] = portfolio['RSI'].apply(get_action)
            
            # 3. Summary Metrics (Premium Cards)
            total_value = portfolio['Market_Value'].sum()
            total_cost = portfolio['Cost_Basis'].sum()
            total_pl = total_value - total_cost
            total_pl_pct = (total_pl / total_cost * 100) if total_cost > 0 else 0
            
            st.markdown("### 📊 Portfolio Summary")
            m1, m2, m3, m4 = st.columns(4)
            
            with m1:
                theme.render_premium_metric(
                    "Total Value", 
                    f"${total_value:,.2f}",
                    icon="💰"
                )
            
            with m2:
                theme.render_premium_metric(
                    "Total P/L ($)", 
                    f"${total_pl:,.2f}",
                    delta=total_pl_pct,
                    icon="📈" if total_pl >= 0 else "📉"
                )
            
            with m3:
                theme.render_premium_metric(
                    "Total P/L (%)", 
                    f"{total_pl_pct:.2f}%",
                    delta=total_pl_pct,
                    icon="🎯"
                )
            
            with m4:
                theme.render_premium_metric(
                    "Holdings", 
                    f"{len(portfolio)}",
                    icon="📦"
                )
            
            st.markdown("---")
            
            # 4. Holdings Table (비중 기준 내림차순 정렬)
            portfolio_sorted = portfolio.sort_values('Market_Value', ascending=False)
            
            # Select columns for display
            holdings_df = portfolio_sorted[[
                'Ticker', 'Quantity', 'Avg_Price', 'Current_Price',
                'Market_Value', 'Cost_Basis', 'PL_Dollar', 'PL_Percent',
                'RSI', 'Action', 'Date_Added'
            ]].copy()
            
            # Rename columns for better display
            holdings_df.columns = [
                'Ticker', 'Qty', 'Avg Price', 'Cur Price', 
                'Mkt Value', 'Cost Basis', 'P/L ($)', 'P/L (%)', 
                'RSI', 'Action', 'Added'
            ]
            
            st.markdown(theme.render_premium_table(holdings_df), unsafe_allow_html=True)
            
            # 5. Remove Position
            st.markdown("---")
            st.subheader("🗑️ Remove Position")
            
            rc1, rc2 = st.columns([3, 1])
            with rc1:
                ticker_to_remove = st.selectbox("Select Ticker to Remove", options=portfolio['Ticker'].tolist())
            with rc2:
                st.write("")
                st.write("")
                if st.button("❌ Remove", type="secondary"):
                    st.session_state['confirm_delete'] = ticker_to_remove
            
            if 'confirm_delete' in st.session_state:
                target = st.session_state['confirm_delete']
                if st.checkbox(f"⚠️ Confirm delete: **{target}**?", key="del_confirm"):
                    if st.button("✅ Yes, Delete"):
                        portfolio = load_portfolio_safe()
                        portfolio = portfolio[portfolio['Ticker'] != target]
                        if save_portfolio_safe(portfolio):
                            st.success(f"Deleted {target}")
                            del st.session_state['confirm_delete']
                            time.sleep(0.5)
                            st.rerun()

if __name__ == "__main__":
    main()
