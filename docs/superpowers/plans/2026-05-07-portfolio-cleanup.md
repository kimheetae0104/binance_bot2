# binance_bot2 Portfolio Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 포트폴리오 수준으로 코드베이스를 정리 — 치명적 버그(랜덤값 ML) 수정, 데드코드 제거, 중복 파일 삭제, .env.example 추가

**Architecture:** `hybrid_surge_detector.py`의 모든 `random.uniform()` 호출을 실제 Binance OHLCV 데이터 기반 계산으로 교체. ML 확률은 `MLPredictor`에서 가져오되, 모델 미로드 시 모멘텀 점수만 사용. 레포 루트의 개발 산출물 마크다운 18개와 중복 파일들 삭제.

**Tech Stack:** Python 3.10+, ccxt, pandas, scikit-learn/xgboost/lightgbm, loguru, python-dotenv

---

## File Map

| 상태 | 파일 | 변경 내용 |
|---|---|---|
| Modify | `hybrid_surge_detector.py` | `random.uniform()` → 실제 API 데이터 |
| Modify | `smart_strategy.py` | 데드코드 제거 (97-101번째 줄) |
| Delete | `CLEAN_SYSTEM_STRUCTURE.md` ~ `UNIFIED_SCHEDULER_GUIDE.md` (18개 .md) | 개발 산출물 삭제 |
| Delete | `beautiful_dashboard.py`, `enhanced_dashboard.py`, `modern_dashboard.py`, `premium_dashboard.py`, `simple_dashboard.py`, `streamlit_dashboard.py`, `html_dashboard.py`, `sync_dashboard.py` | 중복 대시보드 |
| Delete | `advanced_ml_predictor.py`, `advanced_ml_predictor_complete.py`, `advanced_ml_predictor_new.py` | 중복 ML 예측기 |
| Delete | `FINAL_COMPLETION.py` | 개발 산출물 |
| Create | `.env.example` | README가 참조하는 템플릿 |

---

## Task 1: hybrid_surge_detector.py — 랜덤값 → 실제 데이터

**Files:**
- Modify: `hybrid_surge_detector.py`

현재 문제: `_analyze_momentum()`이 `random.uniform()`으로 가격 변동, 거래량, RSI를 모두 가짜로 생성함. `detect_surge_opportunities()`도 `random.uniform(0.2, 0.8)`으로 ML 확률을 생성함.

수정 방향:
- `HybridSurgeDetector.__init__`이 `BinanceConnector`와 선택적으로 `MLPredictor`를 받도록
- `_analyze_momentum`은 실제 OHLCV fetch 후 계산
- ML 확률은 `MLPredictor.predict()` 사용, 모델 없으면 `None`으로 처리해 하이브리드 점수에서 제외

- [ ] **Step 1: hybrid_surge_detector.py 전체 교체**

```python
"""
하이브리드 급등 감지 시스템
"""

import asyncio
from typing import List, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger

if TYPE_CHECKING:
    from binance_api import BinanceConnector
    from ml_predictor import MLPredictor

@dataclass
class SurgeSignal:
    symbol: str
    surge_score: float
    price_change_1h: float
    price_change_5m: float
    volume_surge: float
    rsi: float
    ml_probability: Optional[float] = None
    timestamp: Optional[datetime] = None


class HybridSurgeDetector:
    def __init__(self, binance: "BinanceConnector", ml_predictor: Optional["MLPredictor"] = None):
        self.binance = binance
        self.ml_predictor = ml_predictor

        self.PRICE_SURGE_5M = 0.01      # 5분 1% 이상 상승
        self.PRICE_SURGE_1H = 0.03      # 1시간 3% 이상 상승
        self.VOLUME_SURGE_RATIO = 1.2   # 평균 대비 1.2배 이상 거래량
        self.RSI_MOMENTUM_MIN = 50
        self.RSI_MOMENTUM_MAX = 95
        self.HYBRID_SCORE_THRESHOLD = 0.25

    async def detect_surge_opportunities(self, symbols: List[str]) -> List[SurgeSignal]:
        logger.info(f"🔍 급등 감지 시작 - {len(symbols)}개 심볼 분석")

        candidates = []
        for symbol in symbols:
            signal = await self._analyze_momentum(symbol)
            if signal and signal.surge_score > 0.1:
                candidates.append(signal)

        if not candidates:
            logger.info("   모멘텀 후보가 없습니다.")
            return []

        logger.info(f"📊 1단계 통과: {len(candidates)}개 후보")

        # ML 확률 추가 (모델 로드된 경우만)
        for candidate in candidates:
            if self.ml_predictor and self.ml_predictor.models:
                try:
                    df = self.binance.fetch_ohlcv(candidate.symbol, '5m', 100)
                    if df is not None and len(df) >= 50:
                        result = self.ml_predictor.predict(df)
                        candidate.ml_probability = result.get('probability', None)
                except Exception as e:
                    logger.warning(f"{candidate.symbol} ML 예측 실패: {e}")
                    candidate.ml_probability = None

        # 하이브리드 점수 계산
        final_signals = []
        for signal in candidates:
            if signal.ml_probability is not None:
                # ML 확률과 모멘텀 점수 합산
                hybrid_score = signal.surge_score * 0.6 + signal.ml_probability * 0.4
            else:
                # 모델 없으면 모멘텀 점수만 사용
                hybrid_score = signal.surge_score

            logger.info(
                f"   {signal.symbol}: 모멘텀 {signal.surge_score:.3f} "
                f"+ ML {signal.ml_probability:.3f if signal.ml_probability is not None else 'N/A'} "
                f"= 하이브리드 {hybrid_score:.3f}"
            )
            signal.surge_score = hybrid_score

            if hybrid_score > self.HYBRID_SCORE_THRESHOLD:
                final_signals.append(signal)
                logger.info(f"      ✅ 임계값 {self.HYBRID_SCORE_THRESHOLD:.2f} 통과!")
            else:
                logger.debug(f"      ❌ 임계값 {self.HYBRID_SCORE_THRESHOLD:.2f} 미달")

        final_signals.sort(key=lambda x: x.surge_score, reverse=True)
        return final_signals

    async def _analyze_momentum(self, symbol: str) -> Optional[SurgeSignal]:
        """실제 OHLCV 데이터로 모멘텀 분석"""
        try:
            df = self.binance.fetch_ohlcv(symbol, '5m', 30)
            if df is None or len(df) < 15:
                return None

            close = df['close']
            volume = df['volume']

            # 5분 가격 변동 (최근 캔들)
            price_change_5m = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2]

            # 1시간 가격 변동 (12봉 * 5분 = 60분)
            lookback_1h = min(12, len(close) - 1)
            price_change_1h = (close.iloc[-1] - close.iloc[-1 - lookback_1h]) / close.iloc[-1 - lookback_1h]

            # 거래량 급등 비율 (최근 / 최근 20봉 평균)
            recent_vol = volume.iloc[-1]
            avg_vol = volume.iloc[-21:-1].mean() if len(volume) > 21 else volume.mean()
            volume_surge = recent_vol / avg_vol if avg_vol > 0 else 1.0

            # RSI 계산 (14봉)
            rsi = self._calc_rsi(close, period=14)

            score = 0.0
            if price_change_5m > self.PRICE_SURGE_5M:
                score += min(price_change_5m * 10, 0.3)
            if price_change_1h > self.PRICE_SURGE_1H:
                score += min(price_change_1h * 5, 0.3)
            if volume_surge > self.VOLUME_SURGE_RATIO:
                score += min((volume_surge - 1) * 0.2, 0.3)
            if self.RSI_MOMENTUM_MIN <= rsi <= self.RSI_MOMENTUM_MAX:
                rsi_score = (rsi - self.RSI_MOMENTUM_MIN) / (self.RSI_MOMENTUM_MAX - self.RSI_MOMENTUM_MIN)
                score += rsi_score * 0.2

            if score > 0:
                return SurgeSignal(
                    symbol=symbol,
                    surge_score=score,
                    price_change_1h=price_change_1h,
                    price_change_5m=price_change_5m,
                    volume_surge=volume_surge,
                    rsi=rsi,
                    timestamp=datetime.now()
                )
            return None

        except Exception as e:
            logger.warning(f"{symbol} 모멘텀 분석 실패: {e}")
            return None

    def _calc_rsi(self, close_series, period: int = 14) -> float:
        """RSI 계산"""
        if len(close_series) < period + 1:
            return 50.0
        delta = close_series.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        last_loss = loss.iloc[-1]
        if last_loss == 0:
            return 100.0
        rs = gain.iloc[-1] / last_loss
        return 100 - (100 / (1 + rs))

    def get_signal_summary(self, signal: SurgeSignal) -> str:
        ml_str = f"{signal.ml_probability:.1%}" if signal.ml_probability is not None else "N/A"
        return (
            f"{signal.symbol}: 점수 {signal.surge_score:.3f} "
            f"(1H: {signal.price_change_1h:.1%}, "
            f"5M: {signal.price_change_5m:.1%}, "
            f"거래량: {signal.volume_surge:.1f}x, "
            f"RSI: {signal.rsi:.0f}, ML: {ml_str})"
        )


async def detect_surge_opportunities_async(
    symbols: List[str],
    binance=None,
    ml_predictor=None,
) -> List[dict]:
    """하이브리드 급등 감지 — 딕셔너리 형태로 반환"""
    if binance is None:
        from config import load_config
        from binance_api import BinanceConnector
        config = load_config()
        binance = BinanceConnector(config)

    detector = HybridSurgeDetector(binance=binance, ml_predictor=ml_predictor)
    signals = await detector.detect_surge_opportunities(symbols)

    dict_signals = []
    for signal in signals:
        try:
            current_price = binance.get_current_price(signal.symbol)
            if not current_price or current_price <= 0:
                logger.warning(f"❌ {signal.symbol} 현재가 조회 실패, 스킵")
                continue
        except Exception as e:
            logger.warning(f"❌ {signal.symbol} 현재가 조회 오류: {e}, 스킵")
            continue

        dict_signals.append({
            'symbol': signal.symbol,
            'hybrid_score': signal.surge_score,
            'signal_type': 'momentum_surge',
            'current_price': current_price,
            'price_change_5m': signal.price_change_5m,
            'price_change_1h': signal.price_change_1h,
            'volume_ratio': signal.volume_surge,
            'rsi': signal.rsi,
            'ml_probability': signal.ml_probability or 0.0,
            'surge_probability': signal.surge_score,
            'signal': signal.surge_score >= detector.HYBRID_SCORE_THRESHOLD,
            'confidence': 'high' if signal.surge_score > 0.5 else 'medium' if signal.surge_score > 0.35 else 'low',
            'timestamp': signal.timestamp or datetime.now(),
        })

    return dict_signals


if __name__ == "__main__":
    async def test():
        from config import load_config
        from binance_api import BinanceConnector
        config = load_config()
        binance = BinanceConnector(config)
        detector = HybridSurgeDetector(binance=binance)
        test_symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT']
        signals = await detector.detect_surge_opportunities(test_symbols)
        print(f"\n🚀 최종 급등 신호: {len(signals)}개")
        for signal in signals:
            print(f"   {detector.get_signal_summary(signal)}")

    asyncio.run(test())
```

- [ ] **Step 2: paper_main.py에서 detect_surge_opportunities_async 호출부 확인 및 수정**

`paper_main.py`에서 `detect_surge_opportunities_async` 호출 부분을 찾아 `binance`와 `ml_predictor` 인자를 전달하도록 수정.

```bash
grep -n "detect_surge_opportunities_async" /Users/gimhuitae/Work/binance_bot2/paper_main.py
```

호출 코드가 아래 패턴이면:
```python
signals = await detect_surge_opportunities_async(symbols)
```
아래로 교체:
```python
signals = await detect_surge_opportunities_async(
    symbols,
    binance=self.binance,
    ml_predictor=self.ml_predictor,
)
```

- [ ] **Step 3: 문법 오류 없는지 확인**

```bash
cd /Users/gimhuitae/Work/binance_bot2 && python -c "from hybrid_surge_detector import HybridSurgeDetector, detect_surge_opportunities_async; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: 커밋**

```bash
cd /Users/gimhuitae/Work/binance_bot2
git add hybrid_surge_detector.py paper_main.py
git commit -m "fix: replace random.uniform() in hybrid_surge_detector with real OHLCV data"
```

---

## Task 2: smart_strategy.py 데드코드 제거

**Files:**
- Modify: `smart_strategy.py:81-101`

`_calculate_allin_size` 메서드의 96번째 줄 `return position_size` 이후에 실행되지 않는 코드가 4줄 있음.

- [ ] **Step 1: 데드코드 제거**

`smart_strategy.py`의 `_calculate_allin_size` 메서드에서 아래 부분을 삭제:

```python
# 삭제 대상 (smart_strategy.py:97-101)
        logger.info(f"💰 올인 매매 포지션: ${position_size:.2f} "
                   f"({position_size/available_balance:.1%} of balance, ML확률:{signal.probability:.1%})")
        
        return position_size
```

최종 `_calculate_allin_size` 메서드는 96번째 줄 `return position_size`로 끝나야 함.

- [ ] **Step 2: 확인**

```bash
cd /Users/gimhuitae/Work/binance_bot2 && python -c "from smart_strategy import SmartTradingStrategy; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: 커밋**

```bash
cd /Users/gimhuitae/Work/binance_bot2
git add smart_strategy.py
git commit -m "fix: remove unreachable code after return in _calculate_allin_size"
```

---

## Task 3: 중복 파일 및 개발 산출물 삭제

**Files:**
- Delete: 18개 마크다운 보고서, 8개 중복 대시보드, 3개 중복 ML 예측기, `FINAL_COMPLETION.py`

- [ ] **Step 1: 개발 산출물 마크다운 삭제 (README.md 제외)**

```bash
cd /Users/gimhuitae/Work/binance_bot2
git rm \
  CLEAN_SYSTEM_STRUCTURE.md \
  COMPLETE_SYSTEM_GUIDE.md \
  COMPLETION_REPORT.md \
  DASHBOARD_CLEANUP_COMPLETE.md \
  DASHBOARD_README.md \
  DATASET_COMPLETION_REPORT.md \
  DATASET_UNIFICATION_REPORT.md \
  FINAL_COMPLETION_REPORT.md \
  FINAL_ML_COMPLETION_REPORT.md \
  FINAL_SYSTEM_REPORT.md \
  FULL_SYSTEM_GUIDE.md \
  PAPER_TRADING_GUIDE.md \
  QUICK_START_GUIDE.md \
  SCHEDULER_UNIFICATION_REPORT.md \
  SYSTEM_CLEANUP_COMPLETE.md \
  SYSTEM_FINAL_COMPLETE.md \
  SYSTEM_READY.md \
  UNIFIED_DASHBOARD_GUIDE.md \
  UNIFIED_SCHEDULER_GUIDE.md
```

- [ ] **Step 2: 중복 대시보드 파일 삭제 (dashboard.py만 유지)**

```bash
cd /Users/gimhuitae/Work/binance_bot2
git rm \
  beautiful_dashboard.py \
  enhanced_dashboard.py \
  modern_dashboard.py \
  premium_dashboard.py \
  simple_dashboard.py \
  streamlit_dashboard.py \
  html_dashboard.py \
  sync_dashboard.py \
  system_dashboard.py
```

- [ ] **Step 3: 중복 ML 예측기 및 개발 산출물 파일 삭제**

```bash
cd /Users/gimhuitae/Work/binance_bot2
git rm \
  advanced_ml_predictor.py \
  advanced_ml_predictor_complete.py \
  advanced_ml_predictor_new.py \
  FINAL_COMPLETION.py
```

- [ ] **Step 4: 커밋**

```bash
cd /Users/gimhuitae/Work/binance_bot2
git commit -m "chore: remove dev artifact markdown reports and duplicate dashboard/ML files"
```

---

## Task 4: .env.example 추가

**Files:**
- Create: `.env.example`

README의 `cp .env.example .env` 안내가 작동하도록 파일 생성.

- [ ] **Step 1: .env.example 생성**

```bash
cat > /Users/gimhuitae/Work/binance_bot2/.env.example << 'EOF'
# Binance API (필수)
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET_KEY=your_secret_key_here
USE_TESTNET=True

# 거래 설정
TRADE_MODE=paper
MIN_USDT_24H_VOLUME=300000
ML_PROB_THRESHOLD=0.55

# 수수료 (BNB 할인 적용 시 0.00075)
TAKER_FEE=0.00075
MAKER_FEE=0.00075
AVG_SLIPPAGE=0.0003

# 텔레그램 알림 (선택)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
EOF
```

- [ ] **Step 2: .gitignore에 .env 포함 여부 확인**

```bash
cat /Users/gimhuitae/Work/binance_bot2/.gitignore 2>/dev/null || echo "No .gitignore"
```

`.env`가 없으면 아래 추가:
```bash
echo ".env" >> /Users/gimhuitae/Work/binance_bot2/.gitignore
```

- [ ] **Step 3: 커밋**

```bash
cd /Users/gimhuitae/Work/binance_bot2
git add .env.example .gitignore
git commit -m "docs: add .env.example and ensure .env is gitignored"
```

---

## Task 5: import 검증 — 전체 모듈 로드 확인

모든 수정 후 핵심 모듈들이 정상 임포트되는지 확인.

- [ ] **Step 1: 핵심 모듈 임포트 테스트**

```bash
cd /Users/gimhuitae/Work/binance_bot2 && python -c "
from config import load_config
from smart_strategy import SmartTradingStrategy
from ml_predictor import MLPredictor
from hybrid_surge_detector import HybridSurgeDetector, detect_surge_opportunities_async
from trading_strategy import TradingStrategy
from features import FeatureEngineering
from utils import ensure_dir
print('✅ 모든 핵심 모듈 임포트 성공')
"
```
Expected: `✅ 모든 핵심 모듈 임포트 성공`

- [ ] **Step 2: main.py 구문 오류 확인**

```bash
cd /Users/gimhuitae/Work/binance_bot2 && python -m py_compile main.py paper_main.py smart_strategy.py hybrid_surge_detector.py ml_predictor.py binance_api.py && echo "✅ 구문 오류 없음"
```
Expected: `✅ 구문 오류 없음`

- [ ] **Step 3: 파일 수 확인 (정리 완료 검증)**

```bash
cd /Users/gimhuitae/Work/binance_bot2
echo "Python 파일:" && ls *.py | wc -l
echo "Markdown 파일:" && ls *.md | wc -l
```
Expected: 마크다운 1개 (`README.md`), Python 파일이 크게 줄어있어야 함

- [ ] **Step 4: 최종 커밋 태그**

```bash
cd /Users/gimhuitae/Work/binance_bot2
git log --oneline
```
