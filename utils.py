"""
로깅 및 유틸리티 함수
"""

import json
import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from loguru import logger
import sys

# 로그 디렉토리 생성
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# 로거 설정
logger.remove()
logger.add(
    sys.stdout,
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}",
    colorize=True
)
logger.add(
    LOG_DIR / "trading_bot.log",
    rotation="10 MB",
    retention="30 days",
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}"
)

def now_iso() -> str:
    """현재 시간을 ISO 형식으로 반환"""
    return datetime.now(timezone.utc).isoformat()

def log_trade(action: str, symbol: str, price: float, quantity: float, **kwargs):
    """거래 로그"""
    trade_data = {
        "timestamp": now_iso(),
        "action": action,
        "symbol": symbol,
        "price": price,
        "quantity": quantity,
        **kwargs
    }
    logger.info(f"TRADE | {json.dumps(trade_data, ensure_ascii=False)}")

def log_signal(symbol: str, probability: float, action: str, **kwargs):
    """신호 로그"""
    signal_data = {
        "timestamp": now_iso(),
        "symbol": symbol,
        "probability": probability,
        "action": action,
        **kwargs
    }
    logger.info(f"SIGNAL | {json.dumps(signal_data, ensure_ascii=False)}")

def ensure_dir(path: str) -> Path:
    """디렉토리 생성"""
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path

def load_json(filepath: str, default=None):
    """JSON 파일 로드"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default or {}

def save_json(data: dict, filepath: str):
    """JSON 파일 저장"""
    try:
        ensure_dir(os.path.dirname(filepath))
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"JSON 저장 실패 {filepath}: {e}")

def format_number(num: float, precision: int = 4) -> str:
    """숫자 포맷팅"""
    if abs(num) >= 1:
        return f"{num:.{min(precision, 2)}f}"
    else:
        return f"{num:.{precision}f}"

def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """퍼센트 변화율 계산"""
    if old_value == 0:
        return 0.0
    return ((new_value - old_value) / old_value) * 100

def check_system_health():
    """시스템 상태 간단 체크"""
    health_status = {
        'timestamp': datetime.now().isoformat(),
        'checks': {}
    }
    
    try:
        # 1. 디스크 공간 체크
        import shutil
        disk_usage = shutil.disk_usage('.')
        free_space_gb = disk_usage.free / (1024**3)
        health_status['checks']['disk_space'] = {
            'status': 'ok' if free_space_gb > 1 else 'warning',
            'free_space_gb': round(free_space_gb, 2)
        }
        
        # 2. 필수 파일 존재 체크
        required_files = ['config.py', 'binance_api.py', 'paper_trading.py', 'dashboard.py']
        missing_files = [f for f in required_files if not Path(f).exists()]
        health_status['checks']['files'] = {
            'status': 'ok' if not missing_files else 'error',
            'missing_files': missing_files
        }
        
        # 3. 데이터 디렉토리 체크
        data_dirs = ['data', 'models', 'logs', 'dashboard_data']
        missing_dirs = [d for d in data_dirs if not Path(d).exists()]
        health_status['checks']['directories'] = {
            'status': 'ok' if not missing_dirs else 'warning',
            'missing_dirs': missing_dirs
        }
        
        return health_status
        
    except Exception as e:
        health_status['checks']['system'] = {
            'status': 'error',
            'error': str(e)
        }
        return health_status

def get_current_top_coins():
    """현재 상위 코인 간단 조회"""
    try:
        from binance_api import BinanceConnector
        from config import load_config
        
        config = load_config()
        binance = BinanceConnector(config)
        
        # 상위 볼륨 코인 조회
        symbols = binance.get_usdt_pairs(min_volume=1000000)[:10]  # 상위 10개
        
        top_coins = []
        for symbol in symbols:
            try:
                price = binance.get_current_price(symbol)
                if price:
                    top_coins.append({
                        'symbol': symbol,
                        'price': price,
                        'timestamp': datetime.now().isoformat()
                    })
            except:
                continue
        
        return top_coins
        
    except Exception as e:
        logger.error(f"상위 코인 조회 실패: {e}")
        return []

def validate_trading_config():
    """트레이딩 설정 유효성 검증"""
    try:
        from config import load_config
        config = load_config()
        
        validation_results = {
            'api_keys': bool(config.BINANCE_API_KEY and config.BINANCE_SECRET_KEY),
            'telegram': bool(config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID),
            'risk_management': all([
                hasattr(config, 'STOP_LOSS_PCT'),
                hasattr(config, 'TRAILING_STOP_PCT'),
                hasattr(config, 'ML_PROB_THRESHOLD')
            ]),
            'trading_params': all([
                hasattr(config, 'INITIAL_BALANCE'),
                hasattr(config, 'MAX_POSITION_SIZE_SPLIT'),
                hasattr(config, 'TAKER_FEE')
            ])
        }
        
        all_valid = all(validation_results.values())
        validation_results['overall'] = all_valid
        
        return validation_results
        
    except Exception as e:
        logger.error(f"설정 검증 실패: {e}")
        return {'overall': False, 'error': str(e)}