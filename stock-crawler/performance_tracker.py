import json
import os
from datetime import datetime
import yfinance as yf

class PerformanceTracker:
    """
    M7 Bot의 신호 추적 및 성과 기록
    """
    
    def __init__(self, log_file='signal_history.json'):
        self.log_file = log_file
        self.history = self.load_history()
    
    def load_history(self):
        """기존 기록 로드"""
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'signals': [], 'performance': {}}
    
    def log_signal(self, ticker, signal, price, filters_passed):
        """
        신호 기록
        
        Args:
            ticker: 종목 코드
            signal: 신호 ('Strong Buy', 'Watch', etc.)
            price: 현재가
            filters_passed: 통과한 필터 정보
        """
        entry = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'ticker': ticker,
            'signal': signal,
            'entry_price': price,
            'filters': filters_passed
        }
        
        self.history['signals'].append(entry)
        self.save_history()
        
        print(f"📝 신호 기록: {ticker} - {signal} @ ${price:.2f}")
    
    def check_performance(self, days_back=7):
        """
        과거 신호의 성과 확인
        
        Args:
            days_back: 며칠 전 신호까지 확인할지
        """
        from datetime import timedelta
        
        cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        print(f"\n{'='*60}")
        print(f"📊 최근 {days_back}일 신호 성과 분석")
        print(f"{'='*60}\n")
        
        strong_buy_signals = [
            s for s in self.history['signals'] 
            if s['signal'] == '🚀 강력 매수 (STRONG BUY)' and s['date'] >= cutoff_date
        ]
        
        if not strong_buy_signals:
            print("⚠️ 최근 강력 매수 신호가 없습니다.")
            return
        
        results = []
        
        for signal in strong_buy_signals:
            ticker = signal['ticker']
            entry_price = signal['entry_price']
            
            # 현재가 조회
            try:
                stock = yf.Ticker(ticker)
                current_price = stock.history(period='1d')['Close'].iloc[-1]
                
                return_pct = ((current_price - entry_price) / entry_price) * 100
                
                results.append({
                    'ticker': ticker,
                    'date': signal['date'],
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'return_pct': return_pct
                })
                
                emoji = "🟢" if return_pct > 0 else "🔴"
                print(f"{emoji} {ticker} ({signal['date']})")
                print(f"   진입가: ${entry_price:.2f}")
                print(f"   현재가: ${current_price:.2f}")
                print(f"   수익률: {return_pct:+.2f}%\n")
                
            except Exception as e:
                print(f"⚠️ {ticker} 데이터 조회 실패: {e}")
        
        # 통계 계산
        if results:
            avg_return = sum(r['return_pct'] for r in results) / len(results)
            winning = len([r for r in results if r['return_pct'] > 0])
            
            print(f"{'='*60}")
            print(f"📈 총 신호: {len(results)}개")
            print(f"🎯 승률: {winning}/{len(results)} ({winning/len(results)*100:.1f}%)")
            print(f"💰 평균 수익률: {avg_return:+.2f}%")
            print(f"{'='*60}\n")
            
            # 성과 기록 저장
            self.history['performance'][datetime.now().strftime('%Y-%m-%d')] = {
                'total_signals': len(results),
                'winning_signals': winning,
                'avg_return': avg_return
            }
            self.save_history()
    
    def save_history(self):
        """기록 저장"""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)


# 사용 예시
if __name__ == "__main__":
    tracker = PerformanceTracker()
    
    # 최근 7일 성과 확인
    tracker.check_performance(days_back=7)
    
    # 최근 30일 성과 확인
    tracker.check_performance(days_back=30)
