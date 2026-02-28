# 🚀 완전 자율형 AI 매매 시스템 - 최종 실행 가이드

## ✅ 시스템 준비 완료!

모든 오류가 해결되었고 시스템이 실행 준비가 완료되었습니다.

### 🎯 즉시 실행 방법

#### 1. 환경 변수 설정 (.env 파일 생성)

```bash
# .env 파일을 생성하고 다음 내용을 입력하세요
cat > .env << 'EOF'
# 바이낸스 API (읽기 전용 권한 권장)
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_SECRET=your_binance_secret_key_here

# 텔레그램 알림 (선택사항)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# 매매 설정 (기본값 사용 가능)
INITIAL_BALANCE=100
MIN_USDT_24H_VOLUME=300000
STOP_LOSS_PCT=2
TRAILING_STOP_PCT=0.8
ML_PROB_THRESHOLD=65
ALLIN_MAX_BALANCE=1000
EOF
```

#### 2. 전체 시스템 실행

```bash
# 모든 컴포넌트 자동 시작
./run_full_system.sh start
```

이 명령어로 다음이 자동 시작됩니다:
- 🤖 페이퍼 트레이딩 봇 (24시간 자동 매매)
- ⏰ 자동 스케줄러 (데이터 수집 및 모델 재학습)
- 🌐 실시간 웹 대시보드 (http://localhost:8501)

#### 3. 대시보드 모니터링

웹 브라우저에서 http://localhost:8501 접속
- 실시간 포트폴리오 상태
- AI 모델 성능
- 거래 내역 및 수익률 차트

### 🔧 개별 실행 옵션

#### 페이퍼 트레이딩만 실행
```bash
/Users/gimhuitae/Work/binance_bot2/.venv-1/bin/python paper_main.py
```

#### 데모 모드 (5분간 실행)
```bash
./run_full_system.sh demo
```

#### 시스템 상태 확인
```bash
./run_full_system.sh status
```

#### 실시간 로그 보기
```bash
./run_full_system.sh logs paper_trading
```

### 📊 매매 전략

#### 단타 매매 설정
- **손절선**: -2% (빠른 손절)
- **빠른 익절**: +1.5%
- **목표 익절**: +3%
- **트레일링**: 0.8%
- **최대 보유**: 3시간

#### 자금 관리
- **올인 모드** (≤ $1000): 95% 투자
- **분할 모드** (> $1000): 최대 5포지션, 20%씩

#### AI 예측
- **매수 신호**: 65% 이상 확률
- **5개 모델 앙상블**: XGBoost, LightGBM, RandomForest 등

### ⚡ 자동화된 작업들

- **매일 09:00**: 전체 데이터 수집 + AI 모델 재학습
- **매일 21:00**: 데이터 업데이트 + 성능 분석  
- **매시간**: 활성 심볼 캐시 업데이트
- **2분마다**: 시장 스캔 + 자동 매매 실행

### 🛡️ 안전 기능

- ✅ 페이퍼 트레이딩 (실제 자금 손실 없음)
- ✅ 자동 손절/익절 시스템
- ✅ 포지션 크기 제한
- ✅ 오류 복구 및 재시작
- ✅ 텔레그램 알림

### 🚨 시스템 관리

#### 시작/중지
```bash
./run_full_system.sh start     # 시스템 시작
./run_full_system.sh stop      # 시스템 중지
./run_full_system.sh restart   # 재시작
```

#### 로그 확인
```bash
./run_full_system.sh logs paper_trading  # 트레이딩 로그
./run_full_system.sh logs scheduler      # 스케줄러 로그
tail -f logs/paper_trading.log           # 실시간 로그
```

### 📈 예상 성과

이 시스템은 다음과 같은 기능으로 설계되었습니다:
- **24시간 무인 운영**: 휴일/주말 관계없이 자동 매매
- **AI 기반 예측**: 300+ 심볼에서 최적 신호 선택
- **리스크 관리**: 빠른 손절과 트레일링 익절
- **지속적 학습**: 매일 새로운 데이터로 모델 재학습

### 🔍 문제 해결

#### 자주 발생하는 문제

1. **봇이 시작되지 않는 경우**
   ```bash
   # 환경변수 확인
   cat .env
   
   # 수동 테스트
   /Users/gimhuitae/Work/binance_bot2/.venv-1/bin/python -c "from config import load_config; print(load_config().__dict__)"
   ```

2. **대시보드 접속 불가**
   ```bash
   # 포트 확인
   lsof -i :8501
   
   # 수동 실행
   ./run_full_system.sh dashboard
   ```

3. **로그 확인**
   ```bash
   # 오류 로그만 보기
   grep -i error logs/paper_trading.log
   
   # 최근 100줄
   tail -100 logs/paper_trading.log
   ```

### 🎉 최종 체크리스트

- [ ] .env 파일 생성 및 API 키 설정
- [ ] `./run_full_system.sh start` 실행
- [ ] http://localhost:8501 대시보드 접속 확인
- [ ] 텔레그램 알림 수신 확인 (설정시)
- [ ] 첫 시장 스캔 및 신호 발견 확인

---

## 🚀 지금 바로 시작하기!

```bash
# 1. API 키 설정
nano .env

# 2. 시스템 시작
./run_full_system.sh start

# 3. 대시보드 접속
# 브라우저에서 http://localhost:8501
```

**축하합니다! 완전 자율형 AI 매매 시스템이 준비되었습니다! 🎉**

---
*주의: 이 시스템은 페이퍼 트레이딩으로 실제 자금 손실 없이 안전하게 테스트할 수 있습니다. 실제 거래 전에 충분한 검증을 권장합니다.*
