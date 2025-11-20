import json
import os
from datetime import datetime, timedelta
import yfinance as yf
from performance_tracker import PerformanceTracker

def generate_weekly_summary():
    """
    주간 성과 요약 리포트 생성
    """
    tracker = PerformanceTracker()
    
    print("="*70)
    print("📊 M7 Bot 주간 성과 요약")
    print("="*70)
    print()
    
    # 최근 7일 성과 확인
    print("[1] 최근 7일 신호 성과 분석")
    print("-"*70)
    tracker.check_performance(days_back=7)
    
    # 최근 30일 성과 확인
    print("\n[2] 최근 30일 신호 성과 분석")
    print("-"*70)
    tracker.check_performance(days_back=30)
    
    # HTML 리포트 생성
    generate_performance_html(tracker)
    
    print("\n" + "="*70)
    print("✅ 주간 리포트 생성 완료!")
    print("📄 파일: performance_summary.html")
    print("="*70)


def generate_performance_html(tracker):
    """
    성과 분석 HTML 리포트 생성
    """
    history = tracker.history
    
    # 최근 30일 신호 필터링
    cutoff_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    recent_signals = [
        s for s in history['signals']
        if s['date'] >= cutoff_date
    ]
    
    # 강력 매수 신호만 추출
    strong_buy_signals = [
        s for s in recent_signals
        if '강력 매수' in s['signal'] or 'STRONG BUY' in s['signal']
    ]
    
    # 성과 계산
    performance_rows = ""
    total_return = 0
    winning_count = 0
    
    for signal in strong_buy_signals:
        ticker = signal['ticker']
        entry_price = signal['entry_price']
        entry_date = signal['date']
        
        try:
            stock = yf.Ticker(ticker)
            current_price = stock.history(period='1d')['Close'].iloc[-1]
            return_pct = ((current_price - entry_price) / entry_price) * 100
            
            total_return += return_pct
            if return_pct > 0:
                winning_count += 1
            
            color = "green" if return_pct > 0 else "red"
            emoji = "🟢" if return_pct > 0 else "🔴"
            
            performance_rows += f"""
            <tr>
                <td>{emoji}</td>
                <td style="font-weight:bold;">{ticker}</td>
                <td>{entry_date}</td>
                <td>${entry_price:.2f}</td>
                <td>${current_price:.2f}</td>
                <td style="color: {color}; font-weight: bold;">{return_pct:+.2f}%</td>
            </tr>
            """
        except Exception as e:
            performance_rows += f"""
            <tr>
                <td>⚠️</td>
                <td>{ticker}</td>
                <td>{entry_date}</td>
                <td>${entry_price:.2f}</td>
                <td colspan="2">데이터 조회 실패</td>
            </tr>
            """
    
    # 통계 계산
    total_signals = len(strong_buy_signals)
    win_rate = (winning_count / total_signals * 100) if total_signals > 0 else 0
    avg_return = (total_return / total_signals) if total_signals > 0 else 0
    
    # HTML 생성
    html_content = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>M7 Bot 성과 분석</title>
    <style>
        body {{ font-family: 'Malgun Gothic', sans-serif; margin: 0; padding: 20px; background-color: #f4f4f9; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
        h1 {{ text-align: center; color: #333; }}
        .date {{ text-align: center; color: #666; margin-bottom: 30px; }}
        
        .stats-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 30px; }}
        .stat-box {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; }}
        .stat-value {{ font-size: 2em; font-weight: bold; margin: 10px 0; }}
        .stat-label {{ font-size: 0.9em; opacity: 0.9; }}
        
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }}
        th, td {{ padding: 12px; border-bottom: 1px solid #ddd; text-align: center; }}
        th {{ background-color: #f8f9fa; color: #333; font-weight: bold; }}
        
        .info-box {{ background-color: #e3f2fd; padding: 20px; border-radius: 10px; border-left: 4px solid #2196f3; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 M7 Bot 성과 분석 리포트</h1>
        <div class="date">생성일: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}</div>
        
        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-label">총 신호 수</div>
                <div class="stat-value">{total_signals}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">승률</div>
                <div class="stat-value">{win_rate:.1f}%</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">평균 수익률</div>
                <div class="stat-value">{avg_return:+.2f}%</div>
            </div>
        </div>
        
        <h2>📈 최근 30일 강력 매수 신호 성과</h2>
        <table>
            <thead>
                <tr>
                    <th>상태</th>
                    <th>종목</th>
                    <th>신호 날짜</th>
                    <th>진입가</th>
                    <th>현재가</th>
                    <th>수익률</th>
                </tr>
            </thead>
            <tbody>
                {performance_rows if performance_rows else '<tr><td colspan="6">최근 30일 강력 매수 신호가 없습니다.</td></tr>'}
            </tbody>
        </table>
        
        <div class="info-box">
            <h3>💡 참고사항</h3>
            <ul>
                <li>이 리포트는 "강력 매수 (STRONG BUY)" 신호만 추적합니다.</li>
                <li>수익률은 현재가 기준으로 계산되며, 실제 매도 시점과 다를 수 있습니다.</li>
                <li>5중 필터를 모두 통과한 신호만 기록됩니다.</li>
                <li>과거 성과가 미래 수익을 보장하지 않습니다.</li>
            </ul>
        </div>
    </div>
</body>
</html>
    """
    
    # 파일 저장
    with open('performance_summary.html', 'w', encoding='utf-8') as f:
        f.write(html_content)


if __name__ == "__main__":
    generate_weekly_summary()
