import yfinance as yf
import pandas as pd
import os
import webbrowser
import json
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import asyncio
from telegram import Bot
from advanced_technical_filter import AdvancedTechnicalFilter

# --- Configuration ---
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(os.path.dirname(script_dir), 'config.json')
output_html = os.path.join(script_dir, 'ultimate_v2_report.html')

# Load Telegram Config
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

BOT_TOKEN = config['telegram']['bot_token']
CHAT_ID = config['telegram']['chat_id']

# Stock Groups & Thresholds
GROUPS = {
    'A': {'stocks': ['NVDA', 'TSLA'], 'buy_rsi': 25, 'sell_rsi': 65, 'desc': '고변동성'},
    'B': {'stocks': ['META', 'AMZN', 'GOOGL'], 'buy_rsi': 30, 'sell_rsi': 70, 'desc': '중변동성'},
    'C': {'stocks': ['AAPL', 'MSFT'], 'buy_rsi': 35, 'sell_rsi': 75, 'desc': '저변동성'}
}

ALL_STOCKS = []
for g in GROUPS.values():
    ALL_STOCKS.extend(g['stocks'])
ALL_STOCKS.extend(['QQQ', '^TNX'])  # Add QQQ and 10-Year Treasury

# Sentiment Analyzer
analyzer = SentimentIntensityAnalyzer()

# --- Data Fetching ---
print("데이터 수집 중 (M7 + QQQ + 금리)...")
data = yf.download(ALL_STOCKS, period='1y', auto_adjust=False, group_by='ticker')

if data.empty:
    print("데이터 다운로드 실패. 인터넷 연결을 확인하세요.")
    exit()

# --- STEP 1: Market Filters ---
print("\n[STEP 1] 시장 필터 분석 중...")

# Filter 1A: QQQ Trend
if 'QQQ' not in data.columns:
    print("QQQ 데이터를 찾을 수 없습니다.")
    exit()

qqq = data['QQQ'][['Close']].copy()
qqq['MA120'] = qqq['Close'].rolling(window=120).mean()
qqq_price = qqq['Close'].iloc[-1]
qqq_ma120 = qqq['MA120'].iloc[-1]
qqq_prev_close = qqq['Close'].iloc[-2]

is_market_uptrend = qqq_price > qqq_ma120
daily_return = (qqq_price - qqq_prev_close) / qqq_prev_close * 100
is_market_crash = daily_return < -3.0

# Filter 1B: Interest Rate (^TNX)
if '^TNX' not in data.columns:
    print("금리 데이터를 찾을 수 없습니다.")
    tnx_spike = False
    tnx_price = 0
    tnx_change = 0
else:
    tnx = data['^TNX'][['Close']].copy()
    tnx_price = tnx['Close'].iloc[-1]
    tnx_prev = tnx['Close'].iloc[-2]
    tnx_change = (tnx_price - tnx_prev) / tnx_prev * 100
    tnx_spike = tnx_change > 5.0  # 5% spike

# Overall Market Status
market_blocked = (not is_market_uptrend) or tnx_spike

market_status = "✅ 안전 (Safe)"
market_color = "green"
if not is_market_uptrend:
    market_status = "⚠️ 하락장 (Downtrend)"
    market_color = "orange"
if tnx_spike:
    market_status = "🚨 금리 급등 (Rate Spike)"
    market_color = "red"
if is_market_crash:
    market_status = "🚨 시장 급락 (Crash)"
    market_color = "darkred"

print(f"시장 상태: {market_status}")
print(f"QQQ: ${qqq_price:.2f} (120일선: ${qqq_ma120:.2f})")
print(f"금리(^TNX): {tnx_price:.2f}% (전일 대비: {tnx_change:+.2f}%)")

# --- STEP 2, 3 & 4: Individual Stock Analysis ---
results = []
strong_buy_list = []
chart_htmls = {}  # 차트 HTML 저장

for group_name, group_info in GROUPS.items():
    buy_th = group_info['buy_rsi']
    sell_th = group_info['sell_rsi']
    
    for ticker in group_info['stocks']:
        if ticker not in data.columns:
            print(f"Warning: {ticker} data missing.")
            continue
            
        df = data[ticker][['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        
        # Indicators
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Current Values
        current_price = df['Close'].iloc[-1]
        current_rsi = df['RSI'].iloc[-1]
        ma20 = df['MA20'].iloc[-1]
        ma60 = df['MA60'].iloc[-1]
        
        is_golden_cross = ma20 > ma60
        
        # STEP 2: RSI & Chart Check
        step2_pass = current_rsi < buy_th and is_golden_cross
        
        # STEP 3: News Sentiment (only if Step 2 passed)
        sentiment_score = 0
        sentiment_label = "중립"
        news_block = False
        
        if step2_pass and not market_blocked:
            print(f"\n[STEP 2 통과] {ticker} - 뉴스 감성 분석 중...")
            try:
                stock = yf.Ticker(ticker)
                news = stock.news
                
                if news and len(news) > 0:
                    # Analyze top 3 news headlines
                    scores = []
                    for item in news[:3]:
                        title = item.get('title', '')
                        if title:
                            vs = analyzer.polarity_scores(title)
                            scores.append(vs['compound'])
                    
                    if scores:
                        sentiment_score = sum(scores) / len(scores)
                        
                        if sentiment_score <= -0.5:
                            sentiment_label = "🔴 악재"
                            news_block = True
                        elif sentiment_score >= 0.5:
                            sentiment_label = "🟢 호재"
                        else:
                            sentiment_label = "⚪ 중립"
                        
                        print(f"{ticker} 뉴스 감성: {sentiment_label} (점수: {sentiment_score:.2f})")
            except Exception as e:
                print(f"{ticker} 뉴스 분석 실패: {e}")
                sentiment_label = "분석 실패"
        
        # STEP 4: Advanced Technical Filter (only if Step 2 & 3 passed)
        technical_approved = False
        technical_info = ""
        support_info_str = ""
        resistance_info_str = ""
        poc_str = ""
        
        if step2_pass and not market_blocked and not news_block:
            print(f"\n[STEP 3 통과] {ticker} - 고급 기술적 분석 중...")
            try:
                # AdvancedTechnicalFilter 초기화
                tech_filter = AdvancedTechnicalFilter(ticker, df, current_price)
                
                # 지지선/저항선 탐지
                levels = tech_filter.find_support_resistance(lookback=120)
                print(f"  - 지지선 {len(levels['support'])}개, 저항선 {len(levels['resistance'])}개 탐지")
                
                # 매물대 분석
                volume_profile = tech_filter.calculate_volume_profile(lookback=60)
                poc_price = volume_profile['poc']
                if poc_price:
                    poc_str = f"${poc_price:.2f}"
                    print(f"  - POC (매물대): ${poc_price:.2f}")
                
                # 매수 조건 체크
                buy_check = tech_filter.check_buy_conditions(
                    support_tolerance=0.03,  # 지지선 +3% 이내
                    resistance_range=0.05     # 상단 5% 구간
                )
                
                technical_approved = buy_check['buy_approved']
                
                # 기술적 분석 정보 구성
                if buy_check['support_info']:
                    si = buy_check['support_info']
                    support_info_str = f"지지선 ${si['price']:.2f} 근접 (+{si['distance_pct']:.1f}%, 강도: {si['strength']})"
                    print(f"  ✅ {support_info_str}")
                else:
                    support_info_str = "주요 지지선 근접 없음"
                    print(f"  ❌ {support_info_str}")
                
                if buy_check['no_overhead_resistance']:
                    resistance_info_str = "상단 5% 구간 내 강한 저항 없음"
                    print(f"  ✅ {resistance_info_str}")
                else:
                    ri = buy_check['resistance_info']
                    nearest = ri['nearest']
                    resistance_info_str = f"저항선 ${nearest['price']:.2f} 존재 (강도: {nearest['strength']})"
                    print(f"  ❌ {resistance_info_str}")
                
                technical_info = f"{support_info_str} | {resistance_info_str}"
                
                # 매수 승인 시 차트 생성
                if technical_approved:
                    print(f"  🎯 고급 기술적 조건 통과! 차트 생성 중...")
                    chart_html = tech_filter.generate_plotly_chart(
                        ma20=df['MA20'],
                        ma60=df['MA60']
                    )
                    chart_htmls[ticker] = chart_html
                
            except Exception as e:
                print(f"{ticker} 고급 기술적 분석 실패: {e}")
                technical_info = f"분석 실패: {str(e)}"
        
        # Final Signal Determination
        signal = "관망 (Hold)"
        signal_color = "black"
        
        if market_blocked:
            signal = "매수 금지 (Market)"
            signal_color = "gray"
        elif news_block:
            signal = "악재 차단 (News)"
            signal_color = "brown"
        elif step2_pass and not technical_approved and technical_info:
            signal = "기술적 조건 미달"
            signal_color = "orange"
        elif step2_pass and technical_approved:
            signal = "🚀 강력 매수 (STRONG BUY)"
            signal_color = "green"
            strong_buy_list.append({
                'ticker': ticker,
                'price': current_price,
                'rsi': current_rsi,
                'sentiment': sentiment_label,
                'technical': technical_info
            })
        elif current_rsi > sell_th:
            signal = "매도 (SELL)"
            signal_color = "red"
        
        results.append({
            'group': group_name,
            'ticker': ticker,
            'price': current_price,
            'rsi': current_rsi,
            'threshold': f"{buy_th} / {sell_th}",
            'sentiment': sentiment_label,
            'support': support_info_str if support_info_str else "-",
            'resistance': resistance_info_str if resistance_info_str else "-",
            'poc': poc_str if poc_str else "-",
            'signal': signal,
            'signal_color': signal_color,
            'technical_info': technical_info
        })

# --- Telegram Notification ---
async def send_telegram_message(message):
    """텔레그램 메시지 전송 (타임아웃 및 재시도 로직 포함)"""
    from telegram.request import HTTPXRequest
    
    # 타임아웃 설정: 연결 20초, 읽기 30초
    request = HTTPXRequest(connection_pool_size=8, connect_timeout=20.0, read_timeout=30.0)
    bot = Bot(token=BOT_TOKEN, request=request)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='HTML')
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  재시도 {attempt + 1}/{max_retries - 1}...")
                await asyncio.sleep(2)  # 2초 대기 후 재시도
            else:
                raise e
    return False


if strong_buy_list:
    print(f"\n🚀 강력 매수 신호 {len(strong_buy_list)}개 발견! 텔레그램 전송 중...")
    
    telegram_msg = f"🤖 <b>M7 봇 V2 알림</b>\n\n"
    telegram_msg += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    telegram_msg += f"🚀 <b>강력 매수 신호 ({len(strong_buy_list)}개)</b>\n\n"
    
    for item in strong_buy_list:
        telegram_msg += f"• <b>{item['ticker']}</b>\n"
        telegram_msg += f"  가격: ${item['price']:.2f}\n"
        telegram_msg += f"  RSI: {item['rsi']:.1f}\n"
        telegram_msg += f"  뉴스: {item['sentiment']}\n"
        telegram_msg += f"  기술: {item['technical']}\n\n"
    
    telegram_msg += f"시장 상태: {market_status}\n"
    telegram_msg += f"금리: {tnx_price:.2f}% ({tnx_change:+.2f}%)"
    
    try:
        asyncio.run(send_telegram_message(telegram_msg))
        print("✅ 텔레그램 전송 완료!")
    except Exception as e:
        print(f"❌ 텔레그램 전송 실패: {e}")
else:
    print("\n📭 강력 매수 신호 없음. 텔레그램 전송 생략.")

# --- HTML Generation ---
today_str = datetime.now().strftime('%Y년 %m월 %d일 %H:%M')

html_rows = ""
for r in results:
    html_rows += f"""
    <tr>
        <td class="group-{r['group']}">{r['group']}</td>
        <td style="font-weight:bold;">{r['ticker']}</td>
        <td>${r['price']:.2f}</td>
        <td style="color: {'red' if r['rsi'] > 70 else 'blue' if r['rsi'] < 30 else 'black'}">{r['rsi']:.2f}</td>
        <td>{r['threshold']}</td>
        <td>{r['sentiment']}</td>
        <td style="font-size: 0.85em;">{r['support']}</td>
        <td style="font-size: 0.85em;">{r['resistance']}</td>
        <td>{r['poc']}</td>
        <td style="color: {r['signal_color']}; font-weight: bold;">{r['signal']}</td>
    </tr>
    """

crash_alert = ""
if is_market_crash:
    crash_alert = """
    <div class="alert-box">
        🚨 시장 급락 경보! (QQQ -3% 이상 하락)<br>
        신규 진입은 최대 2종목까지만 제한적으로 허용하세요.
    </div>
    """

# 차트 섹션 생성
charts_section = ""
if chart_htmls:
    charts_section = "<h2 style='margin-top: 40px; color: #333;'>📊 고급 기술적 분석 차트</h2>"
    for ticker, chart_html in chart_htmls.items():
        charts_section += f"<div style='margin-bottom: 30px;'>{chart_html}</div>"

html_content = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ultimate M7 V2 봇 리포트</title>
    <style>
        body {{ font-family: 'Malgun Gothic', sans-serif; margin: 0; padding: 20px; background-color: #f4f4f9; }}
        .container {{ max-width: 1400px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
        h1 {{ text-align: center; color: #333; }}
        h2 {{ color: #555; border-bottom: 2px solid #ddd; padding-bottom: 10px; }}
        .date {{ text-align: center; color: #666; margin-bottom: 20px; }}
        .version-badge {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 5px 15px; border-radius: 20px; font-size: 0.9em; margin-left: 10px; }}
        
        .status-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px; }}
        .status-box {{ padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; }}
        
        .alert-box {{ background-color: #ffebee; color: #c62828; padding: 15px; text-align: center; border: 2px solid #ef5350; border-radius: 10px; margin-bottom: 20px; font-weight: bold; animation: blink 2s infinite; }}
        
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; font-size: 0.9em; }}
        th, td {{ padding: 10px; border-bottom: 1px solid #ddd; text-align: center; }}
        th {{ background-color: #f8f9fa; color: #333; font-weight: bold; position: sticky; top: 0; }}
        
        .group-A {{ color: #e91e63; font-weight: bold; }}
        .group-B {{ color: #2196f3; font-weight: bold; }}
        .group-C {{ color: #4caf50; font-weight: bold; }}
        
        .checklist-box {{ border: 2px dashed #aaa; padding: 20px; border-radius: 10px; background-color: #fff9c4; }}
        .checklist-title {{ font-weight: bold; margin-bottom: 10px; font-size: 1.1em; }}
        
        @keyframes blink {{ 50% {{ opacity: 0.5; }} }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Ultimate M7 봇 V2 종합 리포트<span class="version-badge">고급 기술적 분석</span></h1>
        <div class="date">{today_str} 기준</div>
        
        <div class="status-grid">
            <div class="status-box" style="background-color: {market_color}; color: white;">
                시장 상태 (QQQ)<br>
                {market_status}<br>
                <small>${qqq_price:.2f} / 120일선: ${qqq_ma120:.2f}</small>
            </div>
            <div class="status-box" style="background-color: {'red' if tnx_spike else 'lightgreen'}; color: {'white' if tnx_spike else 'black'};">
                금리 상태 (^TNX)<br>
                {'🚨 급등 경보' if tnx_spike else '✅ 안정'}<br>
                <small>{tnx_price:.2f}% (전일 대비: {tnx_change:+.2f}%)</small>
            </div>
        </div>
        
        {crash_alert}
        
        <h2>📈 종목별 분석 결과</h2>
        <table>
            <thead>
                <tr>
                    <th>그룹</th>
                    <th>종목명</th>
                    <th>현재가</th>
                    <th>RSI</th>
                    <th>기준 (매수/매도)</th>
                    <th>뉴스 감성</th>
                    <th>지지선 정보</th>
                    <th>저항선 정보</th>
                    <th>POC</th>
                    <th>신호</th>
                </tr>
            </thead>
            <tbody>
                {html_rows}
            </tbody>
        </table>
        
        {charts_section}
        
        <div class="checklist-box">
            <div class="checklist-title">✅ [운영 원칙 체크리스트]</div>
            <ul style="margin: 0; padding-left: 20px;">
                <li><strong>자금 배분:</strong> 주식 70% : 현금 30% 비중을 항상 유지하세요.</li>
                <li><strong>손절 규칙:</strong> 개별 종목 -10% 손실 시 절반 매도, -15% 손실 시 전량 매도하세요.</li>
                <li><strong>분할 매수:</strong> 한 번에 사지 말고, 3번에 나누어 진입하세요.</li>
                <li><strong>뉴스 확인:</strong> 악재(🔴) 종목은 감성 점수가 회복될 때까지 대기하세요.</li>
                <li><strong>기술적 조건:</strong> V2에서는 지지선 근접 + 상단 저항 없음 조건을 추가로 확인합니다.</li>
            </ul>
        </div>
    </div>
</body>
</html>
"""

with open(output_html, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"\n✅ 리포트 생성 완료: {output_html}")
webbrowser.open(output_html)
print("🌐 브라우저에서 리포트를 열었습니다.")
