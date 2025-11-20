# Ultimate M7 V2 Bot - 설치 및 사용 가이드

## 📦 1. 라이브러리 설치

### 방법 1: requirements 파일 사용 (권장)
```powershell
pip install -r requirements_v2.txt
```

### 방법 2: 개별 설치
```powershell
# 기존 라이브러리 (이미 설치되어 있을 수 있음)
pip install yfinance pandas vaderSentiment python-telegram-bot

# V2 신규 라이브러리
pip install scipy plotly kaleido
```

### 설치 확인
```powershell
python -c "import scipy; import plotly; import kaleido; print('✅ 모든 라이브러리 설치 완료!')"
```

---

## 🚀 2. 실행 방법

### 방법 1: 배치 파일 사용 (권장)
```
run_ultimate_v2.bat 더블클릭
```

### 방법 2: 직접 실행
```powershell
cd stock-crawler
python ultimate_v2.py
```

---

## 📊 3. V2의 주요 개선사항

### 🎯 강화된 매수 조건
기존 조건 (시장 필터 + RSI + Golden Cross + 뉴스 감성)에 **추가로**:
- ✅ 현재가가 주요 지지선 +3% 이내에 위치
- ✅ 현재가 위 5% 구간 내에 강한 저항선 없음

### 📈 고급 기술적 분석
- **지지선/저항선 자동 탐지**: scipy의 peak detection 알고리즘 사용
- **강도 분류**: 터치 횟수 기반으로 '상/중/하' 등급 부여
- **매물대 분석 (Volume Profile)**: POC (Point of Control) 계산
- **가격 클러스터링**: 유사한 레벨을 자동으로 통합

### 📊 인터랙티브 차트
- **Plotly 캔들스틱 차트**: 확대/축소, 호버 정보 제공
- **지지선/저항선 시각화**: 강도별 색상 구분
- **이동평균선 표시**: MA20, MA60
- **POC 라인**: 매물대 핵심 가격 표시
- **현재가 마커**: 실시간 위치 확인

### 📄 업그레이드된 HTML 리포트
- 기술적 분석 정보 컬럼 추가 (지지선/저항선/POC)
- 매수 추천 종목에 대한 상세 차트 자동 삽입
- 구체적인 매수 근거 표시 (예: "지지선 $150 근접 +2.1%, 강도: 상")

---

## 📋 4. 출력 파일

- **HTML 리포트**: `ultimate_v2_report.html`
- **자동 브라우저 열기**: 실행 완료 시 자동으로 리포트 표시

---

## 🔄 5. 기존 버전과 비교

| 항목 | ultimate_m7_bot.py | ultimate_v2.py |
|------|-------------------|----------------|
| 시장 필터 | ✅ | ✅ |
| RSI + Golden Cross | ✅ | ✅ |
| 뉴스 감성 분석 | ✅ | ✅ |
| 지지선/저항선 분석 | ❌ | ✅ |
| 매물대 (POC) 분석 | ❌ | ✅ |
| 인터랙티브 차트 | ❌ | ✅ |
| 텔레그램 알림 | ✅ | ✅ (기술적 정보 포함) |

---

## ⚠️ 6. 주의사항

### 매수 신호 감소 가능성
V2는 더 엄격한 기술적 조건을 추가했기 때문에, 기존 버전보다 **매수 신호가 적게 발생**할 수 있습니다. 
이는 의도된 동작으로, **신호의 품질을 높이기 위한 것**입니다.

### 데이터 요구사항
- 최소 120일 이상의 가격 데이터 필요
- 거래량 데이터 필수 (Volume Profile 분석용)

### 성능
- 고급 분석으로 인해 실행 시간이 약간 증가할 수 있음 (종목당 +2-3초)
- 차트 생성으로 HTML 파일 크기 증가

---

## 🆘 7. 문제 해결

### "ModuleNotFoundError: No module named 'scipy'"
```powershell
pip install scipy
```

### "ModuleNotFoundError: No module named 'plotly'"
```powershell
pip install plotly
```

### 차트가 표시되지 않음
- 인터넷 연결 확인 (Plotly CDN 사용)
- 브라우저 JavaScript 활성화 확인

### "데이터 다운로드 실패"
- 인터넷 연결 확인
- yfinance 라이브러리 업데이트: `pip install --upgrade yfinance`

---

## 📞 8. 추가 정보

- **기존 버전 유지**: `ultimate_m7_bot.py`는 그대로 유지되므로 언제든 사용 가능
- **병행 사용**: 두 버전을 비교하며 사용 가능
- **설정 공유**: `config.json` 파일을 공유하여 텔레그램 설정 동일하게 적용
