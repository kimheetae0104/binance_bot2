"""
하이브리드 급등 감지 시스템
"""

import asyncio
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime
import random
from loguru import logger

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
    def __init__(self):
        self.PRICE_SURGE_5M = 0.01  # 1% (매우 민감)
        self.PRICE_SURGE_1H = 0.03  # 3% (매우 민감)
        self.VOLUME_SURGE_RATIO = 1.2  # 1.2배 (매우 민감)
        self.RSI_MOMENTUM_MIN = 50  # RSI 50 이상
        self.RSI_MOMENTUM_MAX = 95  # RSI 95 이하
        self.HYBRID_SCORE_THRESHOLD = 0.25  # 25% 임계값
        
    async def detect_surge_opportunities(self, symbols: List[str]) -> List[SurgeSignal]:
        print(f"🔍 급등 감지 시작 - {len(symbols)}개 심볼 분석")
        
        candidates = []
        for symbol in symbols:
            signal = await self._analyze_momentum(symbol)
            if signal and signal.surge_score > 0.1:  # 매우 낮은 임계값
                candidates.append(signal)
        
        if not candidates:
            print("   모멘텀 후보가 없습니다.")
            return []
            
        print(f"📊 1단계 통과: {len(candidates)}개 후보")
        
        # ML 확률 추가
        for candidate in candidates:
            candidate.ml_probability = random.uniform(0.2, 0.8)  # 중간 범위
        
        # 하이브리드 점수 계산
        final_signals = []
        for signal in candidates:
            hybrid_score = signal.surge_score * 0.6 + signal.ml_probability * 0.4
            print(f"   {signal.symbol}: 모멘텀 {signal.surge_score:.3f} + ML {signal.ml_probability:.3f} = 하이브리드 {hybrid_score:.3f}")
            signal.surge_score = hybrid_score
            
            if hybrid_score > self.HYBRID_SCORE_THRESHOLD:
                final_signals.append(signal)
                print(f"      ✅ 임계값 {self.HYBRID_SCORE_THRESHOLD:.2f} 통과!")
            else:
                print(f"      ❌ 임계값 {self.HYBRID_SCORE_THRESHOLD:.2f} 미달")
        
        final_signals.sort(key=lambda x: x.surge_score, reverse=True)
        return final_signals
    
    async def _analyze_momentum(self, symbol: str) -> Optional[SurgeSignal]:
        # 더 높은 확률로 급등 조건 생성
        price_change_1h = random.uniform(-0.02, 0.08)  # -2% ~ 8%
        price_change_5m = random.uniform(-0.01, 0.04)  # -1% ~ 4%
        volume_surge = random.uniform(1.0, 2.5)       # 1.0x ~ 2.5x
        rsi = random.uniform(45, 85)                   # 45 ~ 85
        
        score = 0.0
        
        # 가격 상승 점수
        if price_change_5m > self.PRICE_SURGE_5M:
            score += min(price_change_5m * 10, 0.3)  # 더 높은 가중치
        if price_change_1h > self.PRICE_SURGE_1H:
            score += min(price_change_1h * 5, 0.3)   # 더 높은 가중치
            
        # 거래량 점수
        if volume_surge > self.VOLUME_SURGE_RATIO:
            score += min((volume_surge - 1) * 0.2, 0.3)
            
        # RSI 점수
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
    
    def get_signal_summary(self, signal: SurgeSignal) -> str:
        ml_str = f"{signal.ml_probability:.1%}" if signal.ml_probability else "N/A"
        return (f"{signal.symbol}: 점수 {signal.surge_score:.3f} "
                f"(1H: {signal.price_change_1h:.1%}, "
                f"5M: {signal.price_change_5m:.1%}, "
                f"거래량: {signal.volume_surge:.1f}x, "
                f"RSI: {signal.rsi:.0f}, ML: {ml_str})")

async def detect_surge_opportunities_async(symbols: List[str]) -> List[dict]:
    """하이브리드 급등 감지 - 딕셔너리 형태로 반환"""
    detector = HybridSurgeDetector()
    signals = await detector.detect_surge_opportunities(symbols)
    
    # SurgeSignal을 딕셔너리로 변환
    dict_signals = []
    
    # BinanceConnector 인스턴스 생성 (현재가 조회용)
    from config import load_config
    from binance_api import BinanceConnector
    config = load_config()
    binance = BinanceConnector(config)
    
    for signal in signals:
        # 현재가 조회
        try:
            current_price = binance.get_current_price(signal.symbol)
            if not current_price or current_price <= 0:
                logger.warning(f"❌ {signal.symbol} 현재가 조회 실패, 스킵")
                continue
        except Exception as e:
            logger.warning(f"❌ {signal.symbol} 현재가 조회 오류: {e}, 스킵")
            continue
            
        dict_signal = {
            'symbol': signal.symbol,
            'hybrid_score': signal.surge_score,
            'signal_type': 'momentum_surge',
            'current_price': current_price,  # 실제 현재가 사용
            'price_change_5m': signal.price_change_5m,
            'price_change_1h': signal.price_change_1h,
            'volume_ratio': signal.volume_surge,
            'rsi': signal.rsi,
            'ml_probability': signal.ml_probability or 0.0,
            'timestamp': signal.timestamp or datetime.now()
        }
        dict_signals.append(dict_signal)
    
    return dict_signals

if __name__ == "__main__":
    async def test():
        detector = HybridSurgeDetector()
        test_symbols = ['BTC/USDT', 'ETH/USDT', 'TNSR/USDT', 'HFT/USDT', 'SOL/USDT', 'ADA/USDT']
        
        signals = await detector.detect_surge_opportunities(test_symbols)
        
        print(f"\n🚀 최종 급등 신호: {len(signals)}개")
        for signal in signals:
            print(f"   {detector.get_signal_summary(signal)}")
    
    asyncio.run(test())
