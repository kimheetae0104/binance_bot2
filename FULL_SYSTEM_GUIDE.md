# 🚀 완전 자율형 AI 매매 시스템 사용자 가이드

## 📋 개요

이 시스템은 바이낸스 거래소에서 완전 자동으로 운영되는 AI 기반 암호화폐 매매 봇입니다.

### ✨ 주요 기능

- **완전 자율형 운영**: 24시간 무인 자동 매매
- **다중 시간대 분석**: 5분, 15분, 1시간 봉 종합 분석
- **AI 앙상블 예측**: XGBoost, LightGBM, RandomForest 등 5개 모델
- **단타 매매 전략**: 빠른 익절/손절로 리스크 최소화
- **페이퍼 트레이딩**: 실제 자금 손실 없는 가상 매매
- **실시간 모니터링**: 웹 대시보드와 텔레그램 알림
- **자동 스케줄링**: 정기적 데이터 수집 및 모델 재학습

## 🛠️ 설치 및 설정

### 1. 필수 패키지 설치

```bash
# 패키지 자동 설치
./run_full_system.sh install
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 다음 정보를 입력하세요:

```env
# 바이낸스 API (시장 데이터용만)
BINANCE_API_KEY=your_api_key
BINANCE_SECRET=your_secret_key

# 텔레그램 알림
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# 매매 설정
INITIAL_BALANCE=100
MIN_USDT_24H_VOLUME=300000
STOP_LOSS_PCT=2
TRAILING_STOP_PCT=0.8
ML_PROB_THRESHOLD=65
```

## 🚀 시스템 실행

### 전체 시스템 시작

```bash
# 모든 컴포넌트 자동 시작
./run_full_system.sh start
```

이 명령어로 다음이 자동 시작됩니다:
- 페이퍼 트레이딩 봇
- 자동 스케줄링 시스템  
- 실시간 웹 대시보드 (http://localhost:8501)

### 개별 실행

```bash
# 페이퍼 트레이딩만
python3 paper_main.py

# 스케줄러만
python3 scheduler.py

# 대시보드만
./run_full_system.sh dashboard
```

### 데모 실행

```bash
# 간단한 데모 테스트
./run_full_system.sh demo
```

## 📊 모니터링

### 웹 대시보드

- URL: http://localhost:8501
- 실시간 포트폴리오 상태
- 수익률 차트
- AI 모델 성능
- 거래 내역

### 시스템 상태 확인

```bash
# 전체 상태 확인
./run_full_system.sh status

# 실시간 로그 보기
./run_full_system.sh logs paper_trading
./run_full_system.sh logs scheduler
```

## ⚙️ 매매 전략 설정

### 단타 매매 최적화 설정

- **손절선**: -2% (빠른 손절)
- **빠른 익절**: +1.5% (기본 익절)
- **목표 익절**: +3% (최대 익절)  
- **트레일링**: 0.8% (수익 보호)
- **최대 보유**: 3시간 (강제 청산)

### 자금 관리 전략

- **올인 모드** (≤ $1000): 95% 투자
- **분할 모드** (> $1000): 최대 5개 포지션, 20%씩

### ML 예측 임계값

- **매수 신호**: 65% 이상 확률
- **신뢰도**: High(80%+), Medium(60-80%), Low(60%-)

## 📅 자동 스케줄링

### 정기 작업

- **오전 9시**: 전체 데이터 수집 + 모델 재학습
- **오후 9시**: 데이터 업데이트 + 성능 분석
- **매시간**: 활성 심볼 캐시 업데이트
- **자정**: 일일 성과 리포트
- **일요일 6시**: 주간 최적화

### 자동화된 작업

- 데이터 수집 (300+ USDT 페어)
- 기술지표 계산 (100+ 지표)
- 모델 재학습 및 성능 평가
- 포트폴리오 리밸런싱
- 알림 및 리포트 발송

## 🛡️ 안전 기능

### 리스크 관리

- 페이퍼 트레이딩으로 실제 손실 방지
- 최대 손실 제한 (-2% 손절)
- 포지션 크기 제한
- 시간 기반 강제 청산

### 오류 처리

- 자동 재시작 메커니즘
- API 오류 복구
- 로그 기반 모니터링
- 텔레그램 오류 알림

## 📈 성과 측정

### 주요 지표

- **총 수익률**: 초기 자본 대비 수익
- **승률**: 수익 거래 비율
- **최대 손실**: 최대 연속 손실
- **샤프 비율**: 위험 조정 수익률
- **평균 보유시간**: 포지션 유지 시간

### AI 모델 성능

- **예측 정확도**: 실제 결과 대비 예측 정확도
- **모델별 성능**: 개별 모델 기여도
- **특성 중요도**: 주요 예측 요인
- **앙상블 효과**: 모델 결합 효과

## 🔧 시스템 관리

### 시작/중지

```bash
# 시스템 시작
./run_full_system.sh start

# 시스템 중지
./run_full_system.sh stop

# 재시작
./run_full_system.sh restart
```

### 로그 관리

```bash
# 실시간 로그 보기
./run_full_system.sh logs paper_trading

# 에러 로그 확인
tail -f logs/paper_trading.log | grep ERROR

# 로그 파일 정리 (30일 이상)
find logs/ -name "*.log" -mtime +30 -delete
```

### 데이터 백업

```bash
# 중요 데이터 백업
cp -r models/ models_backup_$(date +%Y%m%d)/
cp -r dashboard_data/ dashboard_backup_$(date +%Y%m%d)/
cp -r paper_trading_data/ trading_backup_$(date +%Y%m%d)/
```

## 🚨 문제 해결

### 일반적인 문제들

1. **봇이 시작되지 않음**
   ```bash
   # 패키지 재설치
   ./run_full_system.sh install
   
   # 환경변수 확인
   python3 -c "from config import load_config; print(load_config().__dict__)"
   ```

2. **예측이 작동하지 않음**
   ```bash
   # 모델 상태 확인
   ls -la models/
   
   # 모델 재훈련
   python3 -c "from paper_main import PaperTradingBot; import asyncio; bot = PaperTradingBot(); asyncio.run(bot.train_models())"
   ```

3. **대시보드 접속 불가**
   ```bash
   # 포트 확인
   lsof -i :8501
   
   # 대시보드 재시작
   ./run_full_system.sh stop
   ./run_full_system.sh start
   ```

### 성능 최적화

1. **메모리 사용량 확인**
   ```bash
   # 프로세스 메모리 모니터링
   ps aux | grep python3
   ```

2. **CPU 사용량 최적화**
   - 배치 크기 조정: `batch_size = 5` (config.py)
   - 스캔 간격 증가: `scan_interval = 300` (5분)

3. **네트워크 최적화**
   - API 요청 제한 준수
   - 동시 요청 수 제한

## 📞 지원

### 로그 분석

```bash
# 오류 패턴 검색
grep -n "ERROR\|FAIL" logs/paper_trading.log

# 성능 통계 확인
grep "성과 리포트" logs/paper_trading.log | tail -5
```

### 시스템 모니터링

```bash
# 디스크 사용량
du -sh . dashboard_data/ models/ logs/

# 메모리 사용량
free -h

# 네트워크 연결
netstat -an | grep :8501
```

## 📚 추가 자료

- [페이퍼 트레이딩 가이드](PAPER_TRADING_GUIDE.md)
- [API 문서](binance_api.py)
- [설정 옵션](config.py)
- [기술지표 목록](features.py)

---

**⚠️ 주의사항**: 이 시스템은 교육 및 연구 목적으로 제작되었습니다. 실제 거래 시에는 충분한 테스트와 위험 관리가 필요합니다.
