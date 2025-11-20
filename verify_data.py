"""
데이터 검증 스크립트
Supabase m7_signals 테이블에서 최근 데이터 조회
"""

from m7_cloud import DBManager
from datetime import datetime

def verify_recent_signals(limit=5):
    """
    Supabase에서 최근 신호 데이터 조회
    
    Args:
        limit: 조회할 데이터 개수 (기본 5개)
    """
    print("="*70)
    print("📡 Supabase 데이터 검증 중...")
    print("="*70)
    print()
    
    try:
        # DB 연결
        db = DBManager()
        print("✅ Supabase 연결 성공!")
        print()
        
        # 최근 데이터 조회
        print(f"📊 최근 {limit}개 신호 조회 중...")
        response = db.supabase.table("m7_signals").select("*").order("created_at", desc=True).limit(limit).execute()
        
        if response.data:
            print(f"✅ {len(response.data)}개 신호 발견!")
            print()
            print("="*70)
            print("최근 신호 내역:")
            print("="*70)
            
            for idx, signal in enumerate(response.data, 1):
                print(f"\n[{idx}] {signal['ticker']} - {signal['signal_type']}")
                print(f"    진입가: ${signal['entry_price']:.2f}")
                print(f"    생성일: {signal['created_at']}")
                print(f"    필터 결과: {signal['filters']}")
                
                # MSFT 신호 특별 표시
                if signal['ticker'] == 'MSFT':
                    print(f"    🎯 MSFT 신호 확인됨!")
            
            print()
            print("="*70)
            print(f"✅ 데이터 검증 완료! 총 {len(response.data)}개 신호 확인")
            print("="*70)
            
            return response.data
        else:
            print("⚠️ 조회된 데이터가 없습니다.")
            print("💡 GitHub Actions가 아직 실행되지 않았거나 데이터가 저장되지 않았을 수 있습니다.")
            return []
            
    except Exception as e:
        print(f"❌ 데이터 조회 실패: {e}")
        print()
        print("💡 확인 사항:")
        print("  1. .env 파일에 SUPABASE_URL과 SUPABASE_KEY가 설정되어 있는지 확인")
        print("  2. Supabase 프로젝트에 m7_signals 테이블이 생성되어 있는지 확인")
        print("  3. 인터넷 연결 상태 확인")
        return None


if __name__ == "__main__":
    # 최근 5개 신호 조회
    signals = verify_recent_signals(limit=5)
    
    if signals:
        print()
        print("🎉 데이터 검증 성공! 대시보드 개발을 진행할 수 있습니다.")
    else:
        print()
        print("⚠️ 데이터가 없거나 조회에 실패했습니다.")
