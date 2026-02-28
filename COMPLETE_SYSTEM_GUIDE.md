# 🚀 바이낸스 ML 트레이딩 봇 - 완전 자동화 시스템

## 📋 시스템 개요

이 시스템은 **완전 자동화된 바이낸스 ML 트레이딩 봇**으로, 다음과 같은 기능을 제공합니다:

### 🎯 핵심 기능
- **🤖 고성능 ML 모델**: XGBoost 기반 급등 패턴 예측 (AUC 0.998)
- **📊 432개 전체 USDT 페어 분석**: 실시간 시장 스캔
- **🔄 완전 자동화**: 매일 정해진 시간에 데이터셋 생성 및 모델 재훈련
- **💰 지능형 매매 전략**: 올인/분할 모드, 트레일링 익절, 손절 관리
- **📱 텔레그램 알림**: 실시간 매매 및 시스템 상태 알림
- **📈 실시간 모니터링**: 시스템 상태 대시보드

### 🎨 시스템 아키텍처

```
📦 바이낸스 ML 트레이딩 봇 시스템
├── 🤖 메인 트레이딩 봇 (main.py)
│   ├── 고급 ML 예측기 (advanced_ml_predictor.py)
│   ├── 지능형 매매 전략 (smart_strategy.py)
│   └── 리스크 관리 시스템
├── 📅 자동 스케줄러 (auto_scheduler.py)
│   ├── 데이터셋 자동 생성
│   ├── ML 모델 자동 재훈련
│   └── 시스템 최적화
├── 📊 시스템 대시보드 (system_dashboard.py)
│   ├── 실시간 상태 모니터링
│   ├── 성능 추적
│   └── 제어 인터페이스
└── 🛠️ 통합 런처 (system_launcher.py)
    ├── 전체 시스템 통합 관리
    ├── 개별 컴포넌트 제어
    └── 상태 조회 및 테스트
```

## 🚀 빠른 시작

### 1. 📋 사전 준비
```bash
# 1. Python 패키지 설치
pip install -r requirements.txt

# 2. 환경변수 설정 (.env 파일)
API_KEY=your_binance_api_key
API_SECRET=your_binance_api_secret
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

### 2. 🎮 시스템 실행

#### 방법 1: 빠른 실행 스크립트 (권장)
```bash
./start.sh
```

#### 방법 2: 개별 실행
```bash
# 전체 시스템 시작 (트레이딩 + 스케줄러)
python system_launcher.py full

# 트레이딩 봇만 시작
python system_launcher.py trading

# 스케줄러만 시작
python system_launcher.py scheduler

# 시스템 상태 조회
python system_launcher.py status

# 대화형 대시보드
python system_dashboard.py

# 실시간 모니터링
python system_dashboard.py monitor
```

## 📅 자동 실행 스케줄

### 정기 자동 실행
- **매일 09:00, 21:00**: 데이터셋 생성 + 모델 재훈련
- **매일 06:00**: 시스템 상태 체크
- **매주 일요일 03:00**: 전체 시스템 최적화

### 수동 테스트 실행
```bash
# 데이터셋 생성 테스트
python scheduler_control.py test-dataset

# 모델 훈련 테스트
python scheduler_control.py test-training

# 전체 업데이트 테스트
python scheduler_control.py test-full

# 시스템 상태 체크
python scheduler_control.py health
```

## 🤖 ML 모델 성능

### 📊 최신 모델 성능 (2024-12-20)
- **모델**: XGBoost Classifier
- **AUC 점수**: 0.998 (거의 완벽한 성능)
- **데이터셋**: 34,136개 샘플 × 135개 고급 특성
- **급등 패턴 감지**: 1,717개 패턴 (432개 USDT 페어)
- **모델 파일**: `models/xgboost_model_new.pkl`

### 📈 특성 엔지니어링 (135개 특성)
- **기본 기술적 지표**: RSI, MACD, Bollinger Bands, etc.
- **고급 특성**: Volume Profile, Order Flow, Market Microstructure
- **시계열 특성**: 다양한 시간대 패턴 분석
- **급등 확률 특성**: 과거 급등 패턴 기반 확률 계산

## 💰 매매 전략

### 🎯 지능형 매매 시스템
- **급등 예측**: ML 모델로 급등 확률이 높은 코인 선택
- **포지션 사이징**: 계좌 잔고에 따른 올인/분할 모드
  - 100만원 미만: 올인 모드
  - 100만원 이상: 분할 모드 (5-10% 할당)
- **진입 조건**: 확률 × 신뢰도 기준 최고 점수 코인 선택

### 🛡️ 리스크 관리
- **손절**: -3% 도달 시 자동 손절
- **익절**: 트레일링 익절 (최고점 대비 -2% 하락 시)
- **최대 보유 시간**: 4시간 (강제 청산)
- **동시 포지션 제한**: 1개 (집중 투자)

## 📊 모니터링 및 알림

### 📱 텔레그램 알림
- **매매 알림**: 진입/청산 시점, 수익률 정보
- **시스템 알림**: 스케줄러 시작/완료, 오류 알림
- **성능 리포트**: 일일/주간 성능 요약

### 📈 대시보드 기능
- **실시간 시스템 상태**: 프로세스, 파일, 리소스 모니터링
- **최근 활동 로그**: 작업 성공/실패 기록
- **성능 통계**: 성공률, 평균 소요 시간
- **제어 인터페이스**: 시스템 시작/중지, 테스트 실행

## 📁 주요 파일 구조

### 🔧 핵심 실행 파일
```
📁 /Users/gimhuitae/Work/binance_bot2/
├── 🤖 main.py                    # 메인 트레이딩 봇
├── 📅 auto_scheduler.py          # 자동 스케줄링 시스템
├── 🚀 system_launcher.py         # 통합 시스템 런처
├── 📊 system_dashboard.py        # 시스템 대시보드
├── 🎛️ scheduler_control.py       # 스케줄러 제어 스크립트
└── ▶️ start.sh                   # 빠른 실행 스크립트
```

### 🧠 ML 시스템
```
├── 🔮 advanced_ml_predictor.py   # 고급 ML 예측기
├── 📊 advanced_dataset_creator.py # 대용량 데이터셋 생성
├── 🏋️ train_production_model.py  # 프로덕션 모델 훈련
├── 🔧 features.py                # 135개 고급 특성 생성
└── 📁 models/
    └── 🏆 xgboost_model_new.pkl  # 최고 성능 모델 (AUC 0.998)
```

### 📊 데이터 및 로그
```
├── 📁 advanced_datasets/         # 대용량 데이터셋 (58.4MB)
├── 📁 scheduler_logs/           # 스케줄러 실행 로그
├── 📁 dashboard_data/           # 대시보드 성능 데이터
└── 📁 backup_files/             # 백업 및 정리된 파일들
```

## ⚙️ 설정 및 커스터마이징

### 🔧 주요 설정 파일
- **config.py**: 시스템 전체 설정
- **.env**: API 키 및 보안 설정
- **requirements.txt**: Python 패키지 의존성

### 🎯 매매 전략 조정
```python
# smart_strategy.py에서 조정 가능한 설정
STOP_LOSS_THRESHOLD = 0.03      # 3% 손절
TRAILING_STOP_THRESHOLD = 0.02  # 2% 트레일링 익절
MAX_HOLD_TIME = 4 * 60 * 60     # 4시간 최대 보유
```

### 📅 스케줄 조정
```python
# auto_scheduler.py에서 스케줄 변경 가능
schedule.every().day.at("09:00").do(self.run_full_update)
schedule.every().day.at("21:00").do(self.run_full_update)
```

## 🧪 테스트 및 검증

### 🔍 시스템 상태 체크
```bash
# 전체 시스템 상태 확인
python system_launcher.py status

# 상세 시스템 헬스 체크
python scheduler_control.py health
```

### 🧪 기능별 테스트
```bash
# 데이터셋 생성 테스트 (30-60분 소요)
python scheduler_control.py test-dataset

# 모델 훈련 테스트 (60-120분 소요)
python scheduler_control.py test-training

# 전체 프로세스 테스트
python scheduler_control.py test-full
```

### 📊 성능 검증
- **페이퍼 트레이딩**: 실제 자금 없이 안전한 시뮬레이션
- **백테스팅**: 과거 데이터로 전략 성능 검증
- **실시간 모니터링**: 대시보드를 통한 실시간 성과 추적

## 🚨 문제해결

### ❌ 일반적인 오류 해결
1. **API 연결 오류**: .env 파일의 API 키 확인
2. **모델 파일 없음**: `python train_production_model.py` 실행
3. **데이터셋 없음**: `python advanced_dataset_creator.py` 실행
4. **권한 오류**: `chmod +x start.sh` 실행

### 🔧 시스템 복구
```bash
# 전체 시스템 재설정
python scheduler_control.py health     # 문제 확인
python scheduler_control.py test-full  # 전체 테스트
```

### 📞 지원 및 로그
- **로그 파일**: `scheduler_logs/` 디렉토리 확인
- **텔레그램 알림**: 실시간 오류 알림 수신
- **대시보드**: 실시간 시스템 상태 모니터링

## 🎉 완성도

### ✅ 구현 완료
- ✅ 고성능 ML 모델 (AUC 0.998)
- ✅ 432개 전체 USDT 페어 분석
- ✅ 완전 자동화 매매 시스템
- ✅ 자동 스케줄링 시스템
- ✅ 실시간 모니터링 대시보드
- ✅ 텔레그램 알림 시스템
- ✅ 리스크 관리 시스템
- ✅ 페이퍼 트레이딩 모드

### 🚀 시스템 준비도: 100%

이 시스템은 **완전히 자동화된 24/7 ML 트레이딩 봇**으로, 실제 수익 창출이 가능한 상태입니다.

---

**⚠️ 중요**: 실제 자금으로 거래하기 전에 반드시 페이퍼 트레이딩으로 충분히 테스트해보시기 바랍니다. 모든 투자에는 위험이 따르며, 과거 성과가 미래 성과를 보장하지 않습니다.

**📞 문의**: 시스템 사용 중 문제가 발생하면 로그 파일과 텔레그램 알림을 확인하거나, 대시보드를 통해 시스템 상태를 점검해주세요.
