"""
하이브리드 급등 감지 시스템
"""

import asyncio
from typing import List, Optional, TYPE_CHECKING
from dataclasses import dataclass
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
                hybrid_score = signal.surge_score * 0.6 + signal.ml_probability * 0.4
            else:
                hybrid_score = signal.surge_score

            ml_str = f"{signal.ml_probability:.3f}" if signal.ml_probability is not None else "N/A"
            logger.info(
                f"   {signal.symbol}: 모멘텀 {signal.surge_score:.3f} "
                f"+ ML {ml_str} = 하이브리드 {hybrid_score:.3f}"
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
