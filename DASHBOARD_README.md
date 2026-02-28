# 🚀 ML Trading Bot Dashboard

바이낸스 ML 트레이딩 봇을 위한 현대적이고 아름다운 실시간 대시보드입니다.

## ✨ 주요 기능

- 📈 **실시간 트레이딩 성과 모니터링**
- 🤖 **ML 모델 성능 분석**
- 💰 **잔고 및 수익/손실 추이**
- 📊 **인터랙티브 차트 및 그래프**
- 🎨 **현대적 다크 테마 UI**
- ⚡ **실시간 데이터 업데이트**

## 🚀 빠른 시작

### 방법 1: 간단한 실행
```bash
./run_dashboard.sh
```

### 방법 2: 통합 메뉴
```bash
./dashboard_launcher.sh
```

메뉴 옵션:
- `1`: Trading Dashboard 실행
- `2`: 실시간 데이터 시뮬레이터만 실행
- `3`: 완전한 시스템 (대시보드 + 실시간 데이터)
- `4`: 테스트 데이터 생성
- `5`: 데이터 초기화

## 📊 대시보드 구성

### 📱 메인 메트릭
- **현재 잔고**: 실시간 잔고와 24시간 변화율
- **오늘 수익**: 당일 총 손익
- **총 거래수**: 전체 거래 건수
- **승률**: 수익 거래 비율
- **ML 정확도**: 모델 예측 정확도

### 📈 차트 섹션
- **포트폴리오 진화**: 시간별 잔고 변화 추이
- **손익 분포**: 거래별 수익/손실 히스토그램
- **승패 비율**: 수익/손실 거래 비율 파이차트
- **ML 성능 지표**: 정확도, 정밀도, 재현율, F1 스코어
- **특성 중요도**: ML 모델의 상위 특성들

### 📋 상세 정보
- **최근 거래**: 최신 20개 거래 내역
- **실시간 통계**: 다양한 성과 지표
- **ML 인사이트**: 예측 신뢰도 분포

## 🎨 UI/UX 특징

### Modern Design
- **다크 테마**: 눈에 편안한 어두운 배경
- **그래디언트 디자인**: 보라-파랑 그래디언트 (`#667eea` - `#764ba2`)
- **반응형 레이아웃**: 모든 디바이스에서 완벽한 표시
- **부드러운 애니메이션**: 호버 효과와 전환 애니메이션

### Interactive Charts
- **Plotly 기반**: 고품질 인터랙티브 차트
- **실시간 업데이트**: 5초마다 데이터 자동 새로고침
- **다양한 시각화**: 라인, 바, 파이, 히스토그램, 레이더 차트
- **상호작용**: 클릭, 드래그, 확대/축소 지원

## 🔧 설정 및 사용법

### ⚙️ 설정 옵션
- **자동 새로고침 주기**: 5초, 10초, 30초, 60초
- **시간 범위 필터**: Last 24h, Last 7d, Last 30d, All Time
- **차트 타입**: 라인, 바, 영역 차트 전환

### 📅 시간대별 분석
- 시간별, 일별, 주별, 월별 성과 분석
- 커스터마이징 가능한 날짜 범위
- 비교 분석 지원

## 💾 데이터 구조

### Performance Data (`performance.json`)
```json
{
  "trades": [...],
  "total_trades": 150,
  "winning_trades": 87,
  "losing_trades": 63,
  "total_profit": 23.45,
  "win_rate": 0.58,
  "max_drawdown": 0.12,
  "sharpe_ratio": 1.34,
  "balance_history": [...]
}
```

### ML Stats (`ml_performance.json`)
```json
{
  "model_accuracy": 0.68,
  "model_precision": 0.72,
  "model_recall": 0.65,
  "model_f1": 0.68,
  "prediction_history": [...],
  "feature_importance": [...]
}
```

## 🔄 실시간 데이터 시뮬레이션

### 데이터 시뮬레이터
- 5초마다 새로운 거래 생성
- 실제 시장 패턴 시뮬레이션
- ML 예측 결과 시뮬레이션

### 테스트 데이터 생성
```bash
python3 generate_dashboard_data.py
```
- 30일간의 거래 시뮬레이션
- ML 성능 메트릭 생성
- 잔고 변화 히스토리 생성

## 🛠️ 기술 스택

- **Frontend**: Streamlit
- **Charts**: Plotly (Interactive charts)
- **Styling**: Custom CSS with modern design
- **Data**: JSON-based data storage
- **Real-time**: Asyncio-based data simulation

## 📁 파일 구조

```
📁 dashboard_system/
├── 🎨 dashboard.py                   # 메인 대시보드 (현대적 UI)
├── 🔄 realtime_data_simulator.py     # 실시간 데이터 생성기
├── 📁 generate_dashboard_data.py     # 테스트 데이터 생성
├── 🚀 dashboard_launcher.sh          # 통합 실행 스크립트
├── 🏃 run_dashboard.sh               # 단일 대시보드 실행
└── 📋 DASHBOARD_README.md            # 이 파일
```

## 🎮 사용 팁

### 💡 실시간 모니터링
- 실시간 데이터 시뮬레이터를 실행하면 5초마다 새로운 거래와 ML 예측이 생성
- 대시보드가 자동으로 업데이트되어 실제 봇의 동작을 시뮬레이션

### 🔍 차트 상호작용
- 차트를 클릭하고 드래그하여 확대/축소 가능
- 호버하면 상세한 데이터 포인트 표시
- 범례를 클릭하여 데이터 시리즈 on/off

### 📱 모바일 지원
- 반응형 디자인으로 모바일 기기에서도 완벽 표시
- 터치 제스처 지원

## 🛠️ 문제해결

### 포트 충돌
```bash
# 포트가 이미 사용 중인 경우
lsof -ti:8501 | xargs kill -9
```

### 패키지 설치 문제
```bash
# 필요한 패키지 재설치
pip3 install --upgrade streamlit plotly loguru pandas numpy
```

### 데이터 초기화
```bash
# 모든 대시보드 데이터 삭제
rm -rf dashboard_data/
python3 generate_dashboard_data.py
```

## 🚀 확장 가능성

- **실제 거래 데이터 연동**: `binance_api.py` 연결
- **알림 시스템**: Telegram/Discord 봇 통합
- **백테스팅 결과**: 히스토리컬 분석 추가
- **다중 전략**: 여러 전략 성과 비교
- **리스크 관리**: VaR, 샤프 비율 등 고급 지표

## 📞 지원

문제가 있거나 제안사항이 있으시면:
- GitHub Issues 생성
- 코드 리뷰 요청
- 새로운 기능 제안

---

**🎉 Happy Trading with Beautiful Dashboard! 🚀**
