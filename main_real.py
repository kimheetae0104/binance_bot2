#!/usr/bin/env python3
"""
실거래용 메인 봇 (main.py를 대체)
페이퍼 트레이딩이 성숙하면 실거래로 전환하는 버전
"""

import asyncio
from loguru import logger
from paper_main import PaperTradingBot

class RealTradingBot(PaperTradingBot):
    """실거래 봇 (페이퍼 트레이딩 봇을 상속)"""
    
    def __init__(self):
        super().__init__()
        logger.warning("🚨 실거래 모드: 실제 자금이 사용됩니다!")
        
        # 실거래용 설정 오버라이드
        self.config.TRADE_MODE = 'real'
        
        # 실거래 엔진으로 변경 (페이퍼 트레이딩 엔진 비활성화)
        # 실거래 준비가 완료되면 BinanceTrader를 사용
        # self.real_trader = BinanceTrader(self.config)
        
    async def initialize(self):
        """실거래 봇 초기화"""
        # 안전 확인
        if not self._safety_checks():
            return False
        
        return await super().initialize()
    
    def _safety_checks(self):
        """실거래 안전 확인"""
        logger.warning("🚨 실거래 안전 확인...")
        
        # API 키 확인
        if not (self.config.BINANCE_API_KEY and self.config.BINANCE_SECRET_KEY):
            logger.error("❌ Binance API 키가 설정되지 않았습니다")
            return False
        
        # 최소 잔고 확인
        try:
            balance = self.binance.get_account_balance()
            usdt_balance = balance.get('USDT', 0)
            if usdt_balance < 50:
                logger.error(f"❌ USDT 잔고 부족: ${usdt_balance:.2f} (최소 $50 필요)")
                return False
        except Exception as e:
            logger.error(f"❌ 잔고 확인 실패: {e}")
            return False
        
        # 사용자 확인
        logger.warning("⚠️ 실거래 모드입니다. 실제 자금이 사용됩니다.")
        logger.warning("⚠️ 페이퍼 트레이딩으로 충분한 테스트를 완료했는지 확인하세요.")
        
        return True

def main():
    """실거래 봇 실행"""
    logger.info("🚨 실거래 봇 시작...")
    
    # 현재는 페이퍼 트레이딩 모드로 실행
    # 실거래 준비가 완료되면 RealTradingBot을 사용
    logger.info("📄 현재는 페이퍼 트레이딩 모드로 실행됩니다.")
    logger.info("📄 실거래 전환은 충분한 테스트 후에 수동으로 활성화하세요.")
    
    bot = PaperTradingBot()  # 안전을 위해 페이퍼 트레이딩으로 시작
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("👋 봇 종료")
    except Exception as e:
        logger.error(f"❌ 봇 실행 오류: {e}")

if __name__ == "__main__":
    main()
