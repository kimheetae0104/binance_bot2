"""
Binance ML 트레이딩 봇 - 메인 실행 파일

이 파일은 트레이딩 봇의 메인 진입점입니다.
안전을 위해 기본적으로 페이퍼 트레이딩 모드로 실행됩니다.
실거래는 main_real.py를 사용하세요.
"""

import asyncio
import sys
from pathlib import Path
from loguru import logger

# 현재 디렉토리를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from paper_main import PaperTradingBot

def main():
    """메인 봇 실행 (페이퍼 트레이딩 모드)"""
    print("🤖 Binance ML 트레이딩 봇")
    print("=" * 50)
    print("📄 안전을 위해 페이퍼 트레이딩 모드로 실행됩니다.")
    print("💰 실거래를 원한다면 main_real.py를 사용하세요.")
    print("=" * 50)
    
    logger.info("🚀 페이퍼 트레이딩 봇 시작...")
    
    try:
        bot = PaperTradingBot()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\n👋 봇을 안전하게 종료합니다...")
        logger.info("사용자에 의해 봇이 종료되었습니다.")
    except Exception as e:
        print(f"\n❌봇 실행 오류: {e}")
        logger.error(f"봇 실행 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
