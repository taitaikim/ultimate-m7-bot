# M7 Bot - 사용 가이드

## 📌 기본 실행 방법

### 1. M7 Bot 실행
```bash
# 방법 1: 배치 파일 더블클릭
run_m7_bot.bat

# 방법 2: 터미널에서 실행
python ultimate_m7_bot.py
```

**실행 결과:**
- 5중 필터 분석 수행
- HTML 리포트 생성 (`ultimate_report.html`)
- 강력 매수 신호 발생 시 텔레그램 알림
- 모든 신호 자동 기록 (`signal_history.json`)

---

## 📊 성과 확인 방법

### 2. 성과 추적
```bash
# 방법 1: 배치 파일 더블클릭
check_performance.bat

# 방법 2: 터미널에서 실행
python performance_tracker.py
```

**확인 내용:**
- 최근 7일 신호 성과
- 최근 30일 신호 성과
- 승률 및 평균 수익률

### 3. 주간 리포트 생성
```bash
# 배치 파일 더블클릭
generate_weekly_report.bat
```

**생성 파일:**
- `performance_summary.html` - 시각화된 성과 리포트
- 총 신호 수, 승률, 평균 수익률 통계
- 개별 신호별 수익률 상세 내역

---

## 🔧 자동화 설정

### Windows 작업 스케줄러 (이미 설정됨)
- **실행 시간**: 매일 23:30 (미국 장 마감 후)
- **실행 파일**: `ultimate_m7_bot.py`
- **자동 작업**: 
  - 데이터 수집
  - 5중 필터 분석
  - 리포트 생성
  - 텔레그램 알림 (강력 매수 신호 시)
  - 신호 기록

---

## 📁 주요 파일 설명

### 실행 파일
- `ultimate_m7_bot.py` - 메인 봇 (5중 필터 시스템)
- `performance_tracker.py` - 성과 추적 시스템
- `weekly_summary.py` - 주간 리포트 생성기

### 배치 파일 (간편 실행)
- `run_m7_bot.bat` - 봇 실행
- `check_performance.bat` - 성과 확인
- `generate_weekly_report.bat` - 주간 리포트 생성

### 데이터 파일
- `signal_history.json` - 모든 신호 기록 (자동 생성)
- `ultimate_report.html` - 일일 분석 리포트
- `performance_summary.html` - 주간 성과 리포트

---

## 🎯 5중 필터 시스템

1. **1차 필터: 거시경제**
   - QQQ 120일 이동평균선 체크
   - 금리(^TNX) 급등 여부 확인

2. **2차 필터: 뉴스 감성**
   - VADER 감성 분석
   - 악재 종목 자동 차단

3. **3차 필터: 차트 기술**
   - RSI 기준 (그룹별 차등 적용)
   - 골든크로스 확인

4. **4차 필터: 옵션 데이터** ⭐
   - IV Rank ≤ 30% 확인
   - Bullish Options Flow 감지

5. **5차 필터: 지지/저항선** ⭐
   - 현재가가 지지선 대비 +3% 이내

---

## 📱 텔레그램 알림

**알림 조건:**
- 5중 필터를 모두 통과한 "강력 매수" 신호만 전송

**알림 내용:**
- 종목명, 현재가, RSI
- 뉴스 감성 분석 결과
- IV Rank, Options Flow, P/C Ratio
- 가장 가까운 지지선 정보

---

## 💡 사용 팁

### 일일 루틴
1. 매일 아침 텔레그램 확인
2. 강력 매수 신호 있으면 `ultimate_report.html` 상세 확인
3. 분할 매수 전략으로 진입 (3회 분할 권장)

### 주간 루틴
1. 매주 일요일 `generate_weekly_report.bat` 실행
2. 성과 리포트 확인
3. 승률 및 수익률 추적
4. 필요시 전략 조정

### 주의사항
- ⚠️ 한 번에 전액 투자 금지 (분할 매수 필수)
- ⚠️ 손절 규칙 준수 (-10%: 절반 매도, -15%: 전량 매도)
- ⚠️ 악재(🔴) 종목은 감성 점수 회복 시까지 대기
- ⚠️ 과거 성과가 미래 수익을 보장하지 않음

---

## 🔍 문제 해결

### 봇이 실행되지 않을 때
```bash
# 1. Python 설치 확인
python --version

# 2. 필요한 라이브러리 재설치
pip install -r requirements.txt

# 3. 수동 실행으로 에러 확인
python ultimate_m7_bot.py
```

### 성과 추적이 안 될 때
- `signal_history.json` 파일이 있는지 확인
- 최소 1회 이상 봇 실행 필요 (신호 기록을 위해)

### 텔레그램 알림이 안 올 때
- `config.json`에 bot_token과 chat_id 확인
- 강력 매수 신호가 실제로 발생했는지 확인 (리포트 참조)

---

## 📞 지원

문제가 발생하면:
1. `ultimate_report.html` 확인
2. 터미널 에러 메시지 확인
3. `signal_history.json` 백업 확인

---

**버전**: 5-Layer Filter System v1.0  
**최종 업데이트**: 2025-11-20
