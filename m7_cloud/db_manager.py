"""
M7 Cloud - Supabase Database Manager
Type-safe cloud database integration with comprehensive error handling
"""

import os
import math
import streamlit as st
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

# .env 파일 로드 (로컬 개발 환경용)
load_dotenv()

class DBManager:
    """
    Supabase 클라우드 DB 연결 및 데이터 관리 클래스
    """
    
    def __init__(self) -> None:
        """
        DBManager 초기화 (Streamlit Secrets 우선, .env 차순)
        """
        self.url: Optional[str] = None
        self.key: Optional[str] = None

        # 1. Streamlit Cloud Secrets 시도
        try:
            if hasattr(st, "secrets") and "SUPABASE_URL" in st.secrets:
                self.url = st.secrets["SUPABASE_URL"]
                self.key = st.secrets["SUPABASE_KEY"]
        except Exception:
            pass
        
        # 2. 로컬 환경변수(.env) 시도
        if not self.url or not self.key:
            self.url = os.getenv("SUPABASE_URL")
            self.key = os.getenv("SUPABASE_KEY")
        
        # 3. 검증
        if not self.url or not self.key:
            # 에러 방지를 위해 로깅만 하고 넘어가거나, 명확한 에러 발생
            # 여기서는 로컬 테스트 편의를 위해 에러를 띄움
            raise ValueError("❌ 접속 정보를 찾을 수 없습니다. (.env 또는 Secrets 확인 필요)")
            
        # 클라이언트 생성
        self.supabase: Client = create_client(self.url, self.key)

    def log_signal(
        self, 
        ticker: str, 
        signal_type: str, 
        entry_price: float, 
        filters: Dict[str, str]
    ) -> Optional[Any]:
        """
        신호 발생 시 DB에 저장 (NaN 안전 처리 포함)
        """
        # 내부 헬퍼 함수: NaN 또는 Infinity를 None으로 변환
        def sanitize_val(val):
            if isinstance(val, float):
                if math.isnan(val) or math.isinf(val):
                    return None
            return val

        safe_price = sanitize_val(float(entry_price))
        
        # 가격이 비정상적이면 저장을 건너뛰거나 0.0으로 처리 (여기선 저장 시도)
        data: Dict[str, Any] = {
            "ticker": ticker,
            "signal_type": signal_type,
            "entry_price": safe_price if safe_price is not None else 0.0,
            "filters": filters,
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            response = self.supabase.table("m7_signals").insert(data).execute()
            print(f"✅ [Cloud DB] {ticker} 신호 저장 성공!")
            return response
        except Exception as e:
            print(f"❌ [Cloud DB] 저장 실패: {e}")
            return None

if __name__ == "__main__":
    try:
        db = DBManager()
        print("✅ DB 연결 성공")
    except Exception as e:
        print(f"❌ 연결 실패: {e}")