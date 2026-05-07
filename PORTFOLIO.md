# 암호화폐 ML 자동매매 시스템 — 개발 포트폴리오

> **Binance ML Trading Bot** (글로벌 마켓, USDT 페어)  
> **Bithumb ML Trading Bot** (국내 KRW 마켓)

---

## 개요

2022년부터 약 2년에 걸쳐 개발한 **머신러닝 기반 암호화폐 자동매매 시스템**입니다.  
ChatGPT가 세상에 처음 등장한 직후부터 LLM을 연구 보조 도구로 활용해 왔으며, 전통적인 기술적 분석과 ML/AI를 결합한 하이브리드 트레이딩 시스템을 설계·구현했습니다.

**핵심 철학**: 단순 지표 매매의 한계를 ML 앙상블로 극복하되, 거짓 신호(False Positive)를 줄이기 위해 다중 기술적 필터를 2단계로 적용합니다.

---

## 기술 스택

| 분류 | 사용 기술 |
|---|---|
| **언어** | Python 3.10+ |
| **ML 프레임워크** | XGBoost, LightGBM, scikit-learn (RF, LR, GBM) |
| **데이터 처리** | pandas, NumPy, SciPy |
| **기술적 지표** | ta (TA-Lib wrapper), 직접 구현 |
| **클래스 불균형** | imbalanced-learn (SMOTE) |
| **특성 스케일링** | RobustScaler (이상치 강건), StandardScaler |
| **거래소 연동** | ccxt (Binance), 직접 REST API 래퍼 (Bithumb) |
| **비동기 처리** | asyncio, ThreadPoolExecutor |
| **스케줄링** | schedule, APScheduler |
| **알림** | Telegram Bot API |
| **로깅** | loguru |
| **모델 직렬화** | joblib, pickle |

---

## 1. 데이터 수집 및 전처리

### 1-1. OHLCV 데이터 수집

```
Binance: ccxt.fetch_ohlcv()  →  5분봉 / 1시간봉 / 1일봉 다중 시간대
Bithumb: 직접 REST API 래퍼  →  Bithumb 고유 포맷 [ts, open, close, high, low, vol]
                                표준 CCXT 포맷 [ts, open, high, low, close, vol] 으로 재정렬
```

Bithumb API는 OHLCV 컬럼 순서가 표준과 달라 (`close`와 `high` 위치가 뒤바뀜)  
모든 다운스트림 코드에서 동일한 DataFrame 구조를 보장하기 위해 수집 단계에서 정규화합니다.

### 1-2. 시계열 데이터 특성과 노이즈 처리

암호화폐 시계열은 금융 데이터 중에서도 노이즈가 극단적으로 심합니다.  
주요 처리 전략:

**① 이동평균 기반 트렌드 분리**
```python
# 단기 노이즈 제거 — MA7 / MA25 / MA99 교차로 추세 방향 판단
ma7  = closes.rolling(7).mean()
ma25 = closes.rolling(25).mean()
ma99 = closes.rolling(99).mean()
trend_valid = (ma7.iloc[-1] > ma25.iloc[-1] > ma99.iloc[-1])
```

**② 볼린저 밴드 — 변동성 정규화**
```python
bb = BollingerBands(closes, window=20, window_dev=2)
bb_width     = (bb_high - bb_low) / bb_mid   # 변동성 비율 피처
bb_position  = (close - bb_low) / (bb_high - bb_low)   # 밴드 내 위치 [0,1]
bb_squeeze   = (bb_width < bb_width.rolling(20).mean())  # 수축 상태 탐지
```
볼린저 밴드 수축(Squeeze) 이후 상단 돌파를 급등 전조 신호로 활용합니다.

**③ ATR (Average True Range) — 동적 손절폭 계산**
```python
atr = AverageTrueRange(high, low, close, window=14).average_true_range()
atr_pct = atr / close  # 가격 대비 변동 비율 → 손절폭을 절대금액이 아닌 변동성 기준으로 설정
```

**④ 거래량 이상치 탐지**
```python
volume_surge = current_volume / volume.rolling(40).mean()
# 평균의 3배 이상 → 비정상 유입 신호
```

**⑤ OBV (On-Balance Volume) 추세 확인**
```python
obv = OnBalanceVolumeIndicator(close, volume).on_balance_volume()
obv_trend_up = (obv > obv.rolling(5).mean())
# 가격 상승 + OBV 증가 → 실수요 동반 상승 판별
```

---

## 2. 피처 엔지니어링 (100+ 기술 지표)

`features.py`의 `FeatureEngineering` 클래스는 4개 카테고리의 피처를 생성합니다:

### 추세 지표 (Trend)
- SMA 5 / 10 / 20 / 50 — 이동평균 크로스오버
- EMA 5 / 10 / 20 / 50 — 지수이동평균
- MACD / MACD Signal / MACD Histogram — 추세 전환 모멘텀
- ADX — 추세 강도 (방향성 무관)

### 모멘텀 지표 (Momentum)
- RSI 14 — 과매수 / 과매도 판별
- Stochastic %K / %D — 단기 반전 신호
- Williams %R — 오실레이터 기반 모멘텀
- Awesome Oscillator — 시장 심리 강도

### 변동성 지표 (Volatility)
- Bollinger Bands (20, ±2σ) — 밴드폭 / 위치 / 수축
- ATR 14 — 평균 진폭 비율
- Keltner Channel — ATR 기반 채널
- Donchian Channel — 최고/최저 브레이크아웃

### 거래량 지표 (Volume)
- OBV — 누적 거래량 추세
- CMF (Chaikin Money Flow) — 자금 흐름
- VPT (Volume Price Trend) — 거래량-가격 연동 추세

### 파생 피처
```python
# 가격 변화율 (로그 수익률)
df['return_1']  = np.log(close / close.shift(1))
df['return_5']  = np.log(close / close.shift(5))
df['return_10'] = np.log(close / close.shift(10))

# 고저 비율
df['hl_ratio']  = (high - low) / close

# 캔들 바디 비율 (허매 캔들 vs 실체 캔들 구분)
df['body_ratio'] = abs(close - open) / (high - low + 1e-8)
```

---

## 3. ML 모델 설계 및 앙상블

### 3-1. 타깃 레이블 정의

단순한 다음 봉 예측 대신, **미래 N 봉 내 +X% 달성** 이진 분류로 정의합니다.

```python
# 6개 봉(30분) 내 +3% 이상 상승 여부
future_return = (close.shift(-PREDICTION_WINDOW) / close - 1)
target = (future_return > SURGE_THRESHOLD).astype(int)
```

이 방식은 단기 노이즈 레이블을 방지하고, 실제 매매에서 의미 있는 수익 구간만 학습합니다.

### 3-2. 클래스 불균형 처리 (SMOTE)

암호화폐 급등은 전체 캔들의 5~10%에 불과한 희귀 이벤트입니다.  
단순 학습 시 모델이 "항상 0(하락)" 예측으로 수렴하는 문제가 발생합니다.

```python
from imblearn.over_sampling import SMOTE

smote = SMOTE(random_state=42, k_neighbors=5)
X_resampled, y_resampled = smote.fit_resample(X_train, y_train)
# 소수 클래스(급등) 샘플을 합성 생성하여 1:1 비율로 균형화
```

### 3-3. 앙상블 구성

**Binance Bot — 3-Tier 앙상블**
```
XGBoost          (트리 기반, 순차 앙상블)
LightGBM         (Leaf-wise 트리, 빠른 학습)
RandomForest     (병렬 배깅, 과적합 방지)
↓
Soft Voting → 평균 확률 → 임계값(0.25) 초과 시 매수 신호
```

**Bithumb Bot — 3-Tier 앙상블**
```
XGBoost          
RandomForest     
LogisticRegression (선형, 과적합 방지 역할)
↓
Soft Voting → 평균 확률 → 임계값(0.60) 초과 시 매수 신호
```

### 3-4. XGBoost 주요 하이퍼파라미터

```python
xgb.XGBClassifier(
    n_estimators=300,
    max_depth=4,           # 얕은 트리 — 암호화폐 노이즈 과적합 방지
    learning_rate=0.05,    # 낮은 학습률 — 안정적 수렴
    subsample=0.8,         # 80% 샘플 랜덤 선택 — 다양성 확보
    colsample_bytree=0.8,  # 80% 피처 랜덤 선택
    scale_pos_weight=5,    # 양성 클래스(급등) 가중치 5배
    use_label_encoder=False,
    eval_metric='logloss'
)
```

`max_depth=4`는 암호화폐처럼 노이즈가 많은 데이터에서 과적합을 막는 핵심 파라미터입니다.  
깊은 트리(depth ≥ 7)는 훈련 세트에서는 높은 정확도를 보이지만 실전에서 급격히 성능이 하락합니다.

### 3-5. 피처 중요도 기반 선택

```python
from sklearn.feature_selection import SelectKBest, f_classif

selector = SelectKBest(f_classif, k=50)  # 상위 50개 피처만 사용
X_selected = selector.fit_transform(X, y)
```

100개 이상의 피처 중 통계적으로 유의미한 50개를 선택해  
차원의 저주(Curse of Dimensionality)를 방지합니다.

---

## 4. 하이브리드 급등 감지 시스템

ML 예측만으로는 False Positive가 많아 필터 레이어를 2단계로 설계했습니다.

```
[1단계] 기술적 멀티 필터
  ├── MA7 > MA25 > MA99 정렬 (상승 추세 확인)
  ├── 볼린저 밴드 상단 돌파 (변동성 확대)
  ├── 20봉 전고점 돌파 +2% (저항선 돌파)
  ├── 거래량 40봉 평균 3배 이상 (실수요 확인)
  ├── 캔들 바디 비율 ≥ 0.6 (명확한 방향성)
  └── OBV 상승 추세 (거래량-가격 동반)

[2단계] ML 앙상블 예측
  └── XGBoost + LightGBM + RF 평균 확률 ≥ 임계값

[최종 신호] 두 조건 모두 충족 시 매수 실행
```

---

## 5. 리스크 관리 — 단계별 트레일링 손절

고정 손절의 한계: 변동성이 높은 시장에서는 고정 손절폭이 너무 좁으면 노이즈에 털리고,  
너무 넓으면 손실이 커집니다.

**Bithumb Bot — 동적 트레일링 손절 테이블**

| 최고 수익률 | 손절선 (최고가 대비) |
|---|---|
| +1.0% | -0.2% |
| +3.0% | -0.4% |
| +5.0% | -0.7% |
| +10.0% | -2.0% |
| +15.0% | -3.0% |
| +50.0%+ | -7.0% (고정) |

수익률이 높아질수록 손절폭을 점진적으로 넓혀 이익을 극대화하면서도 급락 시 자동 청산합니다.

**Binance Bot — ATR 기반 동적 손절**
```python
# 시장 변동성에 비례한 손절폭
stop_loss = entry_price * (1 - max(STOP_LOSS_PCT, atr_pct * 1.5))
```

---

## 6. 매매 전략 — 자본 규모별 분기

```
자본 ≤ $700 (원화 100만원)
  → 올인 매매: 잔고 99.8% 단일 종목 집중 투입
  → 단타 복리: 빠른 회전으로 소액 자본 증식 극대화

자본 > $700
  → 분할 매매: 종목당 최대 20%, 최대 5종목
  → 포트폴리오 분산: 개별 코인 리스크 희석
```

이 전략은 소액에서 시작해 일정 규모 이상이 되면 자동으로 리스크 분산 모드로 전환됩니다.

---

## 7. 시스템 아키텍처

### Binance Bot
```
paper_main.py          # 메인 루프 (페이퍼 트레이딩)
main_real.py           # 실거래 메인
├── HybridSurgeDetector    # 비동기 급등 스캐너
│   ├── _analyze_momentum()    # 실시간 OHLCV 분석
│   └── ML 확률 추가 (2단계 필터)
├── MLPredictor            # 앙상블 예측 엔진
│   ├── XGBoost / LightGBM / RandomForest
│   ├── SMOTE 클래스 균형화
│   └── 피처 중요도 선택 (Top 50)
├── SmartTradingStrategy   # 자본 규모별 전략 분기
│   ├── AllinMode (≤$700)
│   └── SplitMode (>$700)
├── FeatureEngineering     # 100+ 기술 지표 생성
└── dashboard.py           # 실시간 웹 대시보드
```

### Bithumb Bot
```
main.py                # 스케줄러 (3분 매수 + 10초 매도 체크)
src/
├── strategy.py        # ML + 다중 기술적 필터
├── trader.py          # 매수 실행 + 쿨다운 관리
├── trader_sell.py     # 동적 트레일링 손절 실행
├── fetcher.py         # OHLCV 수집 + 피처 생성
├── indicators.py      # ML 훈련용 기술지표
├── position_manager.py# 포지션 / 거래 로그 관리
├── retrain.py         # 자정 모델 재학습
└── shared/
    └── bithumb_api.py # Bithumb REST API 래퍼
```

---

## 8. 개발 과정과 실험 히스토리

### Phase 1 — 단순 지표 매매 (2022)
처음에는 RSI 과매도 + MACD 골든크로스 조합의 단순 규칙 기반 전략으로 시작했습니다.  
백테스트에서는 수익이 났지만 실전에서는 False Positive가 60% 이상이었습니다.  
→ **결론**: 단일 지표는 시장 노이즈를 이기지 못함.

### Phase 2 — 멀티 지표 필터링 (2022~2023)
볼린저 밴드, 거래량 필터, 전고점 돌파 조건을 순차적으로 추가했습니다.  
신호 품질은 개선됐지만, 캔들 패턴 변화에 적응하지 못하는 한계가 명확했습니다.  
→ **결론**: 규칙 기반 시스템은 시장 체제(Regime) 변화에 취약함.

### Phase 3 — ML 도입 + ChatGPT 연구 보조 (2023~)
ChatGPT 등장 이후 LLM을 코드 리뷰, 피처 아이디어 발굴, 논문 요약에 적극 활용했습니다.  
XGBoost를 처음 도입했을 때 훈련 정확도 88%였지만 실전 정확도는 51% — 심각한 과적합.  
→ SMOTE로 클래스 불균형을 해결하고, `max_depth`를 줄이고, 앙상블로 전환해 안정화.

### Phase 4 — 하이브리드 시스템 (현재)
ML 단독이 아닌, **규칙 기반 1차 필터 + ML 2차 검증**의 하이브리드 구조로 재설계했습니다.  
두 시스템의 장점을 결합해 False Positive를 최소화하고 신호 품질을 높였습니다.

---

## 9. 주요 기술적 도전과 해결

| 문제 | 원인 | 해결 방법 |
|---|---|---|
| ML 과적합 | 노이즈 많은 암호화폐 데이터 | max_depth 제한 + SMOTE + Top-50 피처 선택 |
| 클래스 불균형 | 급등은 전체의 5~10% | SMOTE 합성 샘플링으로 1:1 균형화 |
| Bithumb OHLCV 파싱 오류 | 컬럼 순서가 표준과 다름 | 수집 레이어에서 [ts, open, close, high, low, vol] → [ts, open, high, low, close, vol] 재정렬 |
| DataFrame 이터레이션 버그 | `for c in df`는 컬럼명만 반환 | `df['close']`, `df.iloc[-1]`, `.rolling()` API로 전환 |
| 연산자 우선순위 버그 | `> 0.02 & (cond)` → `&`가 `>`보다 높음 | `(expr > 0.02) & (cond)` 괄호 명시화 |
| False Positive 과다 | ML 단독 사용 | 기술적 필터 1단계 → ML 2단계 하이브리드 구조 |

---

## 10. 향후 개선 방향

- **강화학습(RL) 도입**: PPO/SAC로 동적 포지션 사이징 최적화
- **오더북 피처 추가**: 호가창(Orderbook) depth 불균형 신호
- **멀티 타임프레임 앙상블**: 5분봉 + 1시간봉 + 1일봉 별도 모델 합산
- **리얼타임 피처 재학습**: 최근 N일 데이터로 온라인 학습 (Incremental Fitting)
- **Transformer 기반 시계열 모델**: Temporal Fusion Transformer (TFT) 실험

---

## 레포지토리

| 봇 | 거래소 | 링크 |
|---|---|---|
| Binance ML Bot | Binance (USDT) | https://github.com/kimheetae0104/binance_bot2 |
| Bithumb ML Bot | Bithumb (KRW) | https://github.com/kimheetae0104/bithumb-bot |

---

> **면책 조항**: 이 프로젝트는 학습 및 포트폴리오 목적으로 개발되었습니다.  
> 암호화폐 투자는 고위험 자산이며, 투자 손실의 책임은 사용자 본인에게 있습니다.
