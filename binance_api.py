"""
바이낸스 API 연결 및 데이터 수집
"""

import ccxt
import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Any
from loguru import logger
import time
from config import Config

class BinanceConnector:
    """바이낸스 API 연결 관리"""
    
    def __init__(self, config: Config):
        self.config = config
        self.exchange: Optional[ccxt.Exchange] = None
        self.connect()
    
    def connect(self):
        """바이낸스 연결"""
        try:
            self.exchange = ccxt.binance({
                'apiKey': self.config.BINANCE_API_KEY,
                'secret': self.config.BINANCE_SECRET_KEY,
                'sandbox': self.config.USE_TESTNET,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot'  # 현물거래
                }
            })
            
            # 연결 테스트
            self.exchange.load_markets()
            logger.info(f"✅ 바이낸스 연결 성공 ({'테스트넷' if self.config.USE_TESTNET else '메인넷'})")
            
        except Exception as e:
            logger.error(f"❌ 바이낸스 연결 실패: {e}")
            raise
    
    def get_usdt_pairs(self, min_volume: Optional[float] = None) -> List[str]:
        """USDT 페어 목록 조회"""
        try:
            if not self.exchange:
                raise Exception("Exchange not connected")
                
            markets = self.exchange.load_markets()
            usdt_pairs = []
            
            for symbol, market in markets.items():
                if (symbol.endswith('/USDT') and 
                    market.get('active', False) and 
                    market.get('spot', False)):
                    
                    base = symbol.replace('/USDT', '')
                    
                    # 제외할 토큰 필터링
                    if any(exclude in base for exclude in self.config.EXCLUDE_TOKENS):
                        continue
                    
                    usdt_pairs.append(symbol)
            
            # 볼륨 기준 필터링 (옵션)
            if min_volume:
                usdt_pairs = self._filter_by_volume(usdt_pairs, min_volume)
            
            logger.info(f"📊 USDT 페어 수: {len(usdt_pairs)}개")
            return sorted(usdt_pairs)
            
        except Exception as e:
            logger.error(f"USDT 페어 조회 실패: {e}")
            return []
    
    def _filter_by_volume(self, symbols: List[str], min_volume: float) -> List[str]:
        """24h 거래량 기준 필터링"""
        valid_symbols = []
        
        try:
            if not self.exchange:
                return symbols
                
            tickers = self.exchange.fetch_tickers(symbols)
            
            for symbol in symbols:
                if symbol in tickers:
                    ticker = tickers[symbol]
                    volume_24h = ticker.get('quoteVolume', 0) or 0
                    
                    try:
                        if float(volume_24h) >= min_volume:
                            valid_symbols.append(symbol)
                    except (ValueError, TypeError):
                        continue
                        
            logger.info(f"💰 볼륨 필터링: {len(valid_symbols)}/{len(symbols)}개 유지")
            
        except Exception as e:
            logger.warning(f"볼륨 필터링 실패: {e}")
            return symbols
        
        return valid_symbols
    
    def fetch_ohlcv(self, symbol: str, timeframe: str = '5m', limit: int = 500) -> Optional[pd.DataFrame]:
        """OHLCV 데이터 조회"""
        try:
            if not self.exchange:
                return None
                
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            if not ohlcv or len(ohlcv) < 10:
                return None
            
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            # 타임스탬프 변환
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # 데이터 정렬 및 중복 제거
            df = df.sort_index().drop_duplicates()
            
            return df
            
        except Exception as e:
            logger.error(f"{symbol} OHLCV 조회 실패: {e}")
            return None
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """현재가 조회"""
        try:
            if not self.exchange:
                return None
                
            ticker = self.exchange.fetch_ticker(symbol)
            return float(ticker['last'])
        except Exception as e:
            logger.error(f"{symbol} 현재가 조회 실패: {e}")
            return None
    
    def get_account_balance(self) -> Dict[str, float]:
        """계정 잔고 조회"""
        try:
            if not self.exchange:
                return {'USDT': 0.0, 'total_USDT': 0.0}
                
            balance = self.exchange.fetch_balance()
            usdt_info = balance.get('USDT', {})
            return {
                'USDT': float(usdt_info.get('free', 0.0)),
                'total_USDT': float(usdt_info.get('total', 0.0))
            }
        except Exception as e:
            logger.error(f"잔고 조회 실패: {e}")
            return {'USDT': 0.0, 'total_USDT': 0.0}
    
    def place_market_buy_order(self, symbol: str, quote_amount: float) -> Optional[Dict[str, Any]]:
        """시장가 매수 주문"""
        try:
            if not self.exchange:
                return None
                
            # 현재가 조회해서 수량 계산
            current_price = self.get_current_price(symbol)
            if not current_price:
                return None
                
            amount = quote_amount / current_price
            order = self.exchange.create_market_buy_order(symbol, amount)
            logger.info(f"✅ 매수 주문: {symbol} ${quote_amount}")
            return order
        except Exception as e:
            logger.error(f"매수 주문 실패 {symbol}: {e}")
            return None
    
    def place_market_sell_order(self, symbol: str, amount: float) -> Optional[Dict[str, Any]]:
        """시장가 매도 주문"""
        try:
            if not self.exchange:
                return None
                
            order = self.exchange.create_market_sell_order(symbol, amount)
            logger.info(f"✅ 매도 주문: {symbol} {amount}")
            return order
        except Exception as e:
            logger.error(f"매도 주문 실패 {symbol}: {e}")
            return None
    
    def get_open_positions(self) -> Dict[str, Dict]:
        """보유 포지션 조회"""
        try:
            if not self.exchange:
                return {}
                
            balance = self.exchange.fetch_balance()
            positions = {}
            
            for asset, info in balance.items():
                free = info.get('free', 0)
                if free > 0 and asset != 'USDT':
                    symbol = f"{asset}/USDT"
                    current_price = self.get_current_price(symbol)
                    
                    if current_price:
                        positions[symbol] = {
                            'amount': free,
                            'current_price': current_price,
                            'value_usdt': free * current_price
                        }
            
            return positions
            
        except Exception as e:
            logger.error(f"포지션 조회 실패: {e}")
            return {}
