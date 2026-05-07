# Binance ML 자동매매 봇 — 개발 포트폴리오

> **거래소**: Binance (글로벌 USDT 마켓)  
> **레포**: https://github.com/kimheetae0104/binance_bot2

---

## 개요

2022년부터 약 2년에 걸쳐 개발한 **머신러닝 기반 Binance 암호화폐 자동매매 시스템**입니다.  
ChatGPT가 세상에 처음 등장한 직후부터 LLM을 연구 보조 도구로 활용해 왔으며,  
전통적인 기술적 분석과 ML/AI를 결합한 하이브리드 트레이딩 시스템을 설계·구현했습니다.

**핵심 철학**: 단순 지표 매매의 한계를 ML 앙상블로 극복하되,  
거짓 신호(False Positive)를 줄이기 위해 다중 기술적 필터를 2단계로 적용합니다.

---

## 기술 스택

| 분류 | 사용 기술 |
|---|---|
| **언어** | Python 3.10+ |
| **ML 프레임워크** | XGBoost, LightGBM, scikit-learn (RandomForest, GradientBoosting) |
| **데이터 처리** | pandas, NumPy, SciPy |
| **기술적 지표** | ta (TA-Lib wrapper), 직접 구현 |
| **클래스 불균형** | imbalanced-learn (SMOTE) |
| **특성 스케일링** | RobustScaler (이상치 강건), StandardScaler |
| **거래소 연동** | ccxt (Binance REST / WebSocket) |
| **비동기 처리** | asyncio, ThreadPoolExecutor |
| **스케줄링** | APScheduler |
| **알림** | Telegram Bot API |
| **로깅** | loguru |
| **모델 직렬화** | joblib |

---

## 시스템 아키텍처

```
paper_main.py / main_real.py    # 메인 루프 (페이퍼 / 실거래 선택)
├── HybridSurgeDetector         # 비동기 급등 스캐너 (전체 USDT 페어 스캔)
│   ├── _analyze_momentum()         # 실시간 OHLCV → 모멘텀 점수 계산
│   └── ML 확률 추가 (2단계 필터)
├── MLPredictor                 # 앙상블 예측 엔진
│   ├── XGBoost / LightGBM / RandomForest
│   ├── SMOTE 클래스 균형화
│   └── 피처 중요도 선택 (Top 50)
├── SmartTradingStrategy        # 자본 규모별 전략 분기
│   ├── AllinMode  (≤ $700)    # 잔고 99.8% 단일 종목 집중 투입
│   └── SplitMode  (> $700)    # 종목당 최대 20%, 최대 5종목 분산
├── FeatureEngineering          # 100+ 기술 지표 생성
└── dashboard.py                # 실시간 웹 대시보드
```

---

## 1. 데이터 수집 및 전처리

### OHLCV 데이터 수집
```python
# ccxt를 통한 다중 시간대 수집
ohlcv_5m  = binance.fetch_ohlcv(symbol, '5m',  limit=200)
ohlcv_1h  = binance.fetch_ohlcv(symbol, '1h',  limit=100)
ohlcv_1d  = binance.fetch_ohlcv(symbol, '1d',  limit=30)
# 반환 형식: [timestamp, open, high, low, close, volume]
```

전체 USDT 마켓(500+ 종목)을 비동기(asyncio)로 병렬 스캔해  
단일 스레드 대비 스캔 속도를 10배 이상 단축했습니다.

### 시계열 노이즈 처리

암호화폐 시계열은 금융 데이터 중에서도 노이즈가 극단적으로 심합니다.

**① 이동평균 기반 추세 분리**
```python
# 단기 노이즈 제거 — MA7 / MA25 / MA99 정렬로 추세 방향 판단
ma7  = closes.rolling(7).mean()
ma25 = closes.rolling(25).mean()
ma99 = closes.rolling(99).mean()
trend_valid = (ma7.iloc[-1] > ma25.iloc[-1] > ma99.iloc[-1])
```

**② 볼린저 밴드 — 변동성 정규화**
```python
bb = BollingerBands(closes, window=20, window_dev=2)
bb_width    = (bb_high - bb_low) / bb_mid         # 변동성 비율 피처
bb_position = (close - bb_low) / (bb_high - bb_low)  # 밴드 내 위치 [0, 1]
bb_squeeze  = bb_width < bb_width.rolling(20).mean()  # 수축 상태 탐지
```
볼린저 밴드 수축(Squeeze) 이후 상단 돌파를 급등 전조 신호로 활용합니다.

**③ ATR — 동적 손절폭 계산**
```python
atr = AverageTrueRange(high, low, close, window=14).average_true_range()
atr_pct = atr / close  # 변동성 기준 손절폭 (고정 % 손절보다 시장 적응력 높음)
```

**④ 거래량 이상치 탐지**
```python
volume_surge = current_volume / volume.rolling(40).mean()
# 평균의 3배 이상 → 비정상 자금 유입 신호
```

**⑤ OBV — 실수요 동반 여부 확인**
```python
obv = OnBalanceVolumeIndicator(close, volume).on_balance_volume()
obv_trend_up = obv > obv.rolling(5).mean()
# 가격 상승 + OBV 동반 증가 → 진짜 매수 vs 허매수 구분
```

---

## 2. 피처 엔지니어링 (100+ 기술 지표)

`features.py`의 `FeatureEngineering` 클래스가 4개 카테고리 피처를 생성합니다.

### 추세 지표 (Trend)
- SMA 5 / 10 / 20 / 50 — 이동평균 크로스오버
- EMA 5 / 10 / 20 / 50 — 지수이동평균
- MACD / Signal / Histogram — 추세 전환 모멘텀
- ADX — 추세 강도 (방향 무관)
- CCI — 가격 편차 기반 트렌드

### 모멘텀 지표 (Momentum)
- RSI 14 — 과매수 / 과매도
- Stochastic %K / %D — 단기 반전
- Williams %R — 오실레이터 모멘텀
- Awesome Oscillator — 시장 심리 강도

### 변동성 지표 (Volatility)
- Bollinger Bands (20, ±2σ) — 밴드폭 / 위치 / 수축
- ATR 14 — 평균 진폭 비율
- Keltner Channel — ATR 기반 채널
- Donchian Channel — 최고/최저 브레이크아웃

### 거래량 지표 (Volume)
- OBV — 누적 거래량 추세
- CMF (Chaikin Money Flow) — 자금 흐름
- VPT (Volume Price Trend) — 거래량-가격 연동

### 파생 피처
```python
# 로그 수익률 (정규 분포에 가깝게 변환)
df['return_1']  = np.log(close / close.shift(1))
df['return_5']  = np.log(close / close.shift(5))
df['return_10'] = np.log(close / close.shift(10))

# 캔들 바디 비율 (허매 캔들 vs 실체 캔들)
df['body_ratio'] = abs(close - open) / (high - low + 1e-8)

# 고저 비율
df['hl_ratio'] = (high - low) / close
```

---

## 3. ML 모델 설계 및 앙상블

### 타깃 레이블 정의

단순한 다음 봉 예측 대신 **미래 N봉 내 +X% 달성** 이진 분류로 정의합니다.

```python
# 6개 봉(30분) 내 +3% 이상 상승 여부
future_return = close.shift(-PREDICTION_WINDOW) / close - 1
target = (future_return > SURGE_THRESHOLD).astype(int)
```

이 방식은 단기 노이즈 레이블을 방지하고,  
실제 매매에서 의미 있는 수익 구간만 학습하게 합니다.

### 클래스 불균형 처리 (SMOTE)

급등은 전체 캔들의 5~10%에 불과한 희귀 이벤트입니다.  
처리 없이 학습하면 모델이 "항상 0(하락)" 예측으로 수렴합니다.

```python
from imblearn.over_sampling import SMOTE

smote = SMOTE(random_state=42, k_neighbors=5)
X_resampled, y_resampled = smote.fit_resample(X_train, y_train)
# 소수 클래스(급등) 합성 샘플 생성 → 1:1 비율로 균형화
```

### 앙상블 구성 (3-Tier Soft Voting)

```
XGBoost          (순차 앙상블, 비선형 패턴 포착)
LightGBM         (Leaf-wise 트리, 빠른 학습, 대용량 피처에 강함)
RandomForest     (병렬 배깅, 과적합 방지 역할)
↓
Soft Voting → 평균 확률 → 임계값(0.25) 초과 시 매수 신호
```

### XGBoost 핵심 파라미터

```python
xgb.XGBClassifier(
    n_estimators=300,
    max_depth=4,           # 얕은 트리 — 암호화폐 노이즈 과적합 방지
    learning_rate=0.05,    # 낮은 학습률 — 안정적 수렴
    subsample=0.8,         # 80% 샘플 랜덤 선택
    colsample_bytree=0.8,  # 80% 피처 랜덤 선택
    scale_pos_weight=5,    # 양성 클래스(급등) 가중치 5배
    eval_metric='logloss'
)
```

`max_depth=4`가 핵심입니다.  
깊은 트리(depth ≥ 7)는 훈련 정확도 88%를 달성하지만 실전에서 51%로 급락했습니다.  
얕은 트리로 제한하자 실전 정확도가 안정화되었습니다.

### 피처 중요도 기반 선택

```python
from sklearn.feature_selection import SelectKBest, f_classif

selector = SelectKBest(f_classif, k=50)  # 통계적으로 유의한 상위 50개
X_selected = selector.fit_transform(X, y)
# 100+개 피처 → 차원의 저주 방지
```

---

## 4. 하이브리드 급등 감지 시스템

ML 예측만으로는 False Positive가 많아 2단계 필터 구조를 설계했습니다.

```
[1단계] 기술적 멀티 필터 (HybridSurgeDetector)
  ├── 5분 가격 변화 ≥ +1%
  ├── 1시간 가격 변화 ≥ +3%
  ├── 거래량 40봉 평균 대비 1.2배 이상
  ├── RSI 50 ~ 95 (과열 직전 모멘텀 구간)
  └── 하이브리드 스코어 ≥ 0.25

[2단계] ML 앙상블 예측
  └── XGBoost + LightGBM + RF 평균 확률 ≥ 0.25

[최종 신호] 두 조건 모두 충족 시 매수 실행
```

---

## 5. 매매 전략 — 자본 규모별 분기

```python
def get_trading_mode(current_balance: float) -> str:
    if current_balance <= 700:   # $700 (원화 약 100만원) 이하
        return 'allin'           # 전체 잔고 99.8% 단일 종목 집중
    else:
        return 'split'           # 종목당 최대 20%, 최대 5종목 분산
```

소액에서 시작해 복리로 자산을 증식하다가, 일정 규모 이상이 되면  
자동으로 분산 모드로 전환해 리스크를 희석합니다.

---

## 6. 리스크 관리

| 항목 | 설정값 | 설명 |
|---|---|---|
| 손절 | -3% | 타이트한 단타 손절 |
| 초기 익절 | +3% | 빠른 이익 실현 |
| 트레일링 스탑 | 최고가 -0.8% | 이익 극대화 후 자동 청산 |
| ATR 기반 손절 | atr_pct × 1.5 | 변동성 높을 때 자동 확대 |
| 최대 보유 시간 | 3시간 | 시간 초과 시 강제 청산 |

---

## 7. 개발 과정과 실험 히스토리

### Phase 1 — 단순 지표 매매 (2022)
RSI 과매도 + MACD 골든크로스 조합의 규칙 기반 전략으로 시작.  
백테스트 수익률은 좋았지만 실전 False Positive 60% 이상.  
→ **결론**: 단일 지표는 시장 노이즈를 이기지 못함.

### Phase 2 — 멀티 지표 필터링 (2022~2023)
볼린저 밴드, 거래량 필터, 전고점 돌파 조건을 순차적으로 추가.  
신호 품질은 개선됐지만 시장 체제(Regime) 변화에 적응하지 못함.  
→ **결론**: 규칙 기반 시스템은 고정된 시장 가정에 의존함.

### Phase 3 — ML 도입 + ChatGPT 연구 보조 활용 (2023~)
ChatGPT 등장 직후부터 LLM을 코드 리뷰, 피처 아이디어 발굴, 논문 요약에 적극 활용.  
XGBoost 첫 도입 시 훈련 정확도 88% → 실전 51% (심각한 과적합).  
SMOTE로 클래스 불균형 해결, `max_depth` 축소, 앙상블 전환 후 안정화.

### Phase 4 — 하이브리드 시스템 (현재)
ML 단독이 아닌 **기술적 필터 1차 + ML 2차**의 하이브리드 구조로 재설계.  
False Positive를 최소화하고 신호 품질을 높임.  
페이퍼 트레이딩(모의 거래) 모드를 먼저 구현해 실전 전 검증 가능하도록 설계.

---

## 8. 주요 기술적 도전과 해결

| 문제 | 원인 | 해결 방법 |
|---|---|---|
| ML 과적합 | 노이즈 많은 암호화폐 데이터 | `max_depth` 제한 + SMOTE + Top-50 피처 선택 |
| 클래스 불균형 | 급등 이벤트가 전체의 5~10% | SMOTE 합성 샘플링으로 1:1 균형화 |
| 전체 마켓 스캔 속도 | 500+ 종목 순차 처리 | asyncio 비동기 병렬 스캔으로 10배 속도 개선 |
| 랜덤 데이터 버그 | `random.uniform()`으로 가짜 OHLCV 생성 | 실제 ccxt OHLCV + 진짜 RSI 계산으로 교체 |
| False Positive 과다 | ML 단독 사용 | 기술적 필터 1단계 → ML 2단계 하이브리드 구조 |

---

## 9. 향후 개선 방향

- **강화학습(RL)**: PPO/SAC로 동적 포지션 사이징 최적화
- **오더북 피처**: 호가창 depth 불균형 신호 추가
- **멀티 타임프레임 앙상블**: 5분봉 / 1시간봉 / 1일봉 별도 모델 합산
- **온라인 학습**: 최근 N일 데이터로 Incremental Fitting
- **Transformer 기반**: Temporal Fusion Transformer(TFT) 시계열 모델 실험

---

> **면책 조항**: 이 프로젝트는 학습 및 포트폴리오 목적으로 개발되었습니다.  
> 암호화폐 투자는 고위험 자산이며, 투자 손실의 책임은 사용자 본인에게 있습니다.
