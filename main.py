"""
M7 Bot - Main Signal Engine (V4.1 Trendline + ATR Edition)
Integration with OpenAI for CIO-style Market Briefing & Risk Management
"""

import os
import sys
import asyncio
import numpy as np
import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
from telegram import Bot
from telegram.request import HTTPXRequest
import openai

# Custom Modules
from m7_cloud import DBManager
from m7_core.strategy_v4 import TrendlineStrategy, RiskManager # V4.1 엔진 탑재

# Load environment variables
load_dotenv()

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Default Trading Config (For Bot Notifications)
DEFAULT_BALANCE = 10000  # 기준 자본금 ($10,000)
DEFAULT_RISK_PCT = 2.0   # 리스크 비율 (2%)
ATR_MULTIPLIER = 2.0     # 손절 거리 계수

# Streamlit Secrets Fallback
if not BOT_TOKEN:
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            BOT_TOKEN = st.secrets.get("TELEGRAM_TOKEN", BOT_TOKEN)
            CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", CHAT_ID)
            OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", OPENAI_API_KEY)
    except: pass

# Stock Groups
GROUPS = {
    'A': {'stocks': ['NVDA', 'TSLA', 'TQQQ'], 'desc': 'High Beta 🚀'},
    'B': {'stocks': ['META', 'AMZN', 'GOOGL', 'XLK'], 'desc': 'Mid Beta ⚖️'},
    'C': {'stocks': ['AAPL', 'MSFT', 'QQQ'], 'desc': 'Low Beta 🛡️'}
}

ALL_STOCKS = [s for g in GROUPS.values() for s in g['stocks']] + ['^TNX']

if OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# ============================================================================
# AI CIO MODULE
# ============================================================================
def generate_ai_briefing(market_summary_text):
    print("🧠 AI CIO가 브리핑을 작성 중입니다...")
    system_prompt = """
    당신은 월스트리트 헤지펀드의 냉철한 CIO입니다.
    V4.1 전략(Trendline Breakout + ATR Sizing)을 기반으로 투자자에게 브리핑합니다.
    
    [작성 원칙]
    1. 톤앤매너: 전문적, 단호함, 하십시오체.
    2. 핵심: 시장의 방향성(QQQ 추세)과 리스크(TNX 금리)를 먼저 언급하십시오.
    3. 신호 해석: '추세선 돌파(Breakout)' 종목이 있다면 강력한 매수 기회임을 강조하고, 없다면 '관망(Hold)'의 중요성을 설파하십시오.
    4. 자금 관리: ATR 기반의 포지션 사이징이 왜 중요한지 한 줄 팁을 포함하십시오.
    """
    try:
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"데이터:\n{market_summary_text}"}
            ],
            temperature=0.3,
            max_tokens=600
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ AI 브리핑 오류: {e}"

# ============================================================================
# CORE FUNCTIONS
# ============================================================================
def analyze_market_condition(data: pd.DataFrame):
    # QQQ Trend Check
    qqq = data['QQQ']['Close']
    ma120 = qqq.rolling(window=120).mean().iloc[-1]
    current_qqq = qqq.iloc[-1]
    is_uptrend = current_qqq > ma120
    
    # TNX Volatility Check
    tnx = data['^TNX']['Close']
    tnx_chg = ((tnx.iloc[-1] - tnx.iloc[-2]) / tnx.iloc[-2]) * 100
    is_safe = tnx_chg < 5.0
    
    status = "✅ Risk On" if is_uptrend and is_safe else "⚠️ Risk Off"
    return is_uptrend and is_safe, status, tnx.iloc[-1]

def analyze_stock_v4(ticker, data):
    print(f"📊 {ticker} V4.1 분석 중...")
    df = data[ticker].copy()
    
    # 1. ATR Calculation
    df['High_Low'] = df['High'] - df['Low']
    df['High_Close'] = np.abs(df['High'] - df['Close'].shift())
    df['Low_Close'] = np.abs(df['Low'] - df['Close'].shift())
    df['TR'] = df[['High_Low', 'High_Close', 'Low_Close']].max(axis=1)
    df['ATR'] = df['TR'].rolling(window=14).mean()
    
    # 2. Strategy Execution
    strategy = TrendlineStrategy(df)
    slope, intercept = strategy.calculate_resistance_line()
    is_breakout, trendline_price = strategy.check_breakout()
    
    current_price = df['Close'].iloc[-1]
    current_atr = df['ATR'].iloc[-1]
    
    # 3. Position Sizing
    shares = RiskManager.calculate_position_size(DEFAULT_BALANCE, DEFAULT_RISK_PCT, current_atr, ATR_MULTIPLIER)
    stop_loss = current_price - (current_atr * ATR_MULTIPLIER)
    
    result = {
        'ticker': ticker,
        'price': current_price,
        'is_breakout': is_breakout,
        'trendline_price': trendline_price,
        'shares': shares,
        'stop_loss': stop_loss,
        'atr': current_atr
    }
    return result

async def send_report(breakout_list, market_status, tnx_val, ai_briefing):
    if not BOT_TOKEN or not CHAT_ID: return
    
    msg = f"🚀 <b>M7 Bot V4.1 Briefing</b>\n\n"
    msg += f"{ai_briefing}\n\n"
    msg += f"━━━━━━━━━━━━━━━━━\n"
    msg += f"📡 <b>Signal Report</b>\n"
    
    if breakout_list:
        for item in breakout_list:
            msg += f"\n🔥 <b>{item['ticker']} BREAKOUT!</b>\n"
            msg += f"• Price: ${item['price']:.2f}\n"
            msg += f"• Target: Buy <b>{item['shares']} shares</b>\n"
            msg += f"• Stop Loss: ${item['stop_loss']:.2f}\n"
            msg += f"• Risk Basis: ${DEFAULT_BALANCE:,.0f} (2% Risk)\n"
    else:
        msg += "\n💤 <b>No Breakout Signals</b>\n모든 종목이 추세선 아래에 있습니다.\n"
        
    msg += f"\n📉 TNX: {tnx_val:.2f}% | Market: {market_status}"

    try:
        request = HTTPXRequest(connection_pool_size=8, connect_timeout=20.0, read_timeout=30.0)
        bot = Bot(token=BOT_TOKEN, request=request)
        await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='HTML')
        print("✅ 텔레그램 전송 완료")
    except Exception as e:
        print(f"❌ 전송 실패: {e}")

# ============================================================================
# MAIN
# ============================================================================
def main():
    print("🚀 M7 Bot V4.1 Engine Start...")
    
    # 1. Data Fetching
    data = yf.download(ALL_STOCKS, period='1y', interval='1d', group_by='ticker', progress=False)
    if data.empty: return
    data = data.ffill().dropna(how='all')
    
    # 2. Market Check
    market_ok, market_status, tnx_val = analyze_market_condition(data)
    
    # 3. Stock Analysis
    breakout_list = []
    signal_summary = ""
    
    for group in GROUPS.values():
        for ticker in group['stocks']:
            if ticker not in data.columns: continue
            
            res = analyze_stock_v4(ticker, data)
            
            # Log for AI
            dist_to_line = res['trendline_price'] - res['price'] if res['trendline_price'] else 0
            signal_summary += f"- {ticker}: ${res['price']:.2f} "
            if res['is_breakout']:
                signal_summary += "(🚨 BREAKOUT!)\n"
                if market_ok: breakout_list.append(res)
            else:
                signal_summary += f"(저항선까지 ${dist_to_line:.2f} 남음)\n"

    # 4. Generate AI Briefing & Send
    market_text = f"Market Status: {market_status}\nTNX: {tnx_val:.2f}%\nSignals:\n{signal_summary}"
    ai_briefing = generate_ai_briefing(market_text)
    
    asyncio.run(send_report(breakout_list, market_status, tnx_val, ai_briefing))
    print("✅ 작업 종료")

if __name__ == "__main__":
    main()
