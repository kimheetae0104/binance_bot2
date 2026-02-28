"""
바이낸스 ML 트레이딩 봇 설정
"""

import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class Config:
    # 거래 설정
    TRADE_MODE = os.getenv('TRADE_MODE', 'paper')
    USE_TESTNET = os.getenv('USE_TESTNET', 'True').lower() == 'true'
    
    # Binance API
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
    BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', '')
    
    # 거래 파라미터
    QUOTE_ASSET = 'USDT'
    MIN_USDT_24H_VOLUME = float(os.getenv('MIN_USDT_24H_VOLUME', '300000'))
    INITIAL_BALANCE = 70.0  # 초기 자본 $70 (원화 10만원, 1430원/달러)
    SPLIT_TRADING_THRESHOLD = 700.0  # $700 (원화 100만원) 초과시 분할매수
    
    # 포지션 크기 전략 - 100만원 기준
    ALLIN_MAX_BALANCE = 700.0  # 원화 100만원($700) 이하는 올인 매매
    MAX_POSITION_SIZE_SPLIT = 0.20  # 분할매수시 종목당 최대 20%
    MAX_POSITIONS_AFTER_SPLIT = 5  # 분할 후 최대 보유 종목 수
    
    # 올인 매매 설정 - BNB 할인 수수료 반영
    ALLIN_SAFETY_MARGIN = 0.998  # 99.8% 전액 투입 (BNB 할인으로 0.2% 수수료 여유분)
    
    # 수수료 - BNB 할인 적용 (이미지 기준: 0.075% 기본 → BNB 할인)
    TAKER_FEE = float(os.getenv('TAKER_FEE', '0.00075'))  # 0.075% (BNB 할인 적용)
    MAKER_FEE = float(os.getenv('MAKER_FEE', '0.00075'))  # 0.075% (BNB 할인 적용)  
    AVG_SLIPPAGE = float(os.getenv('AVG_SLIPPAGE', '0.0003'))  # 낮은 슬리피지
    
    # 리스크 관리 - 단타 매매 최적화
    STOP_LOSS_PCT = 0.03  # -3% 손절 (단타용 타이트 손절)
    TAKE_PROFIT_PCT = 0.03  # +3% 초기 익절 (단타용)
    TRAILING_STOP_PCT = 0.008  # 0.8% 트레일링 스탑 (빠른 이익확정)
    
    # 단타 매매 설정
    SCALPING_MODE = True  # 단타 모드 활성화
    QUICK_EXIT_THRESHOLD = 0.015  # 1.5% 도달시 빠른 익절 고려
    MAX_HOLD_MINUTES = 180  # 최대 3시간 보유 후 강제 청산
    
    # ML 설정 - 하이브리드용 조정  
    ML_PROB_THRESHOLD = float(os.getenv('ML_PROB_THRESHOLD', '0.25'))  # 하이브리드 신호 활용
    PREDICTION_WINDOW = 6  # 6개 캔들 (30분) 예측
    
    # 하이브리드 급등 감지 설정
    HYBRID_MODE = True  # 하이브리드 모드 활성화
    HYBRID_THRESHOLD = 0.25  # 25% 이상 하이브리드 스코어
    FEATURE_WINDOW = 50  # 짧은 기간 특성
    
    # 텔레그램
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # 제외 토큰
    EXCLUDE_TOKENS = [
        'USDC', 'BUSD', 'TUSD', 'PAX',
        'BULL', 'BEAR', 'UP', 'DOWN',
        '3L', '3S', '5L', '5S'
    ]

def load_config():
    """설정 로드"""
    return Config()