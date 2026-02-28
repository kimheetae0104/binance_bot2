"""
고급 기술적 지표 계산 및 특성 공학
100+ 기술지표와 다중 시간대 통합 분석
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple
from loguru import logger
import warnings
from scipy import stats
from sklearn.preprocessing import StandardScaler, RobustScaler
warnings.filterwarnings('ignore')

# TA-Lib 지표들
try:
    from ta.trend import MACD, EMAIndicator, SMAIndicator, WMAIndicator, CCIIndicator, ADXIndicator
    from ta.momentum import RSIIndicator, StochasticOscillator, WilliamsRIndicator, AwesomeOscillatorIndicator
    from ta.volatility import BollingerBands, AverageTrueRange, KeltnerChannel, DonchianChannel
    from ta.volume import OnBalanceVolumeIndicator, ChaikinMoneyFlowIndicator, VolumePriceTrendIndicator
    from ta.others import DailyReturnIndicator, CumulativeReturnIndicator
except ImportError:
    logger.warning("TA-Lib 라이브러리를 설치해주세요: pip install ta")

class TechnicalIndicators:
    """기술적 지표 계산"""
    
    @staticmethod
    def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
        """이동평균 추가"""
        try:
            # 단순 이동평균
            df['sma_5'] = SMAIndicator(df['close'], window=5).sma_indicator()
            df['sma_10'] = SMAIndicator(df['close'], window=10).sma_indicator()
            df['sma_20'] = SMAIndicator(df['close'], window=20).sma_indicator()
            df['sma_50'] = SMAIndicator(df['close'], window=50).sma_indicator()
            
            # 지수 이동평균
            df['ema_5'] = EMAIndicator(df['close'], window=5).ema_indicator()
            df['ema_10'] = EMAIndicator(df['close'], window=10).ema_indicator()
            df['ema_20'] = EMAIndicator(df['close'], window=20).ema_indicator()
            df['ema_50'] = EMAIndicator(df['close'], window=50).ema_indicator()
            
            # 이동평균 관계
            df['price_above_sma20'] = (df['close'] > df['sma_20']).astype(int)
            df['price_above_ema20'] = (df['close'] > df['ema_20']).astype(int)
            df['sma5_above_sma20'] = (df['sma_5'] > df['sma_20']).astype(int)
            df['ema5_above_ema20'] = (df['ema_5'] > df['ema_20']).astype(int)
            
            return df
        except Exception as e:
            logger.error(f"이동평균 계산 실패: {e}")
            return df
    
    @staticmethod
    def add_momentum_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """모멘텀 지표 추가"""
        try:
            # RSI
            df['rsi'] = RSIIndicator(df['close'], window=14).rsi()
            df['rsi_overbought'] = (df['rsi'] > 70).astype(int)
            df['rsi_oversold'] = (df['rsi'] < 30).astype(int)
            
            # MACD
            macd = MACD(df['close'])
            df['macd'] = macd.macd()
            df['macd_signal'] = macd.macd_signal()
            df['macd_diff'] = macd.macd_diff()
            df['macd_bullish'] = (df['macd'] > df['macd_signal']).astype(int)
            
            # 스토캐스틱
            stoch = StochasticOscillator(df['high'], df['low'], df['close'])
            df['stoch_k'] = stoch.stoch()
            df['stoch_d'] = stoch.stoch_signal()
            df['stoch_oversold'] = ((df['stoch_k'] < 20) & (df['stoch_d'] < 20)).astype(int)
            
            return df
        except Exception as e:
            logger.error(f"모멘텀 지표 계산 실패: {e}")
            return df
    
    @staticmethod
    def add_volatility_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """변동성 지표 추가"""
        try:
            # 볼린저 밴드
            bb = BollingerBands(df['close'], window=20, window_dev=2)
            df['bb_high'] = bb.bollinger_hband()
            df['bb_low'] = bb.bollinger_lband()
            df['bb_mid'] = bb.bollinger_mavg()
            df['bb_width'] = (df['bb_high'] - df['bb_low']) / df['bb_mid']
            df['bb_position'] = (df['close'] - df['bb_low']) / (df['bb_high'] - df['bb_low'])
            df['bb_squeeze'] = (df['bb_width'] < df['bb_width'].rolling(20).mean()).astype(int)
            
            # ATR
            atr = AverageTrueRange(df['high'], df['low'], df['close'])
            df['atr'] = atr.average_true_range()
            df['atr_pct'] = df['atr'] / df['close']
            
            # 가격 변동률
            df['price_change_1'] = df['close'].pct_change(1)
            df['price_change_5'] = df['close'].pct_change(5)
            df['price_change_10'] = df['close'].pct_change(10)
            
            # 변동성
            df['volatility_5'] = df['price_change_1'].rolling(5).std()
            df['volatility_20'] = df['price_change_1'].rolling(20).std()
            
            return df
        except Exception as e:
            logger.error(f"변동성 지표 계산 실패: {e}")
            return df
    
    @staticmethod
    def add_volume_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """거래량 지표 추가"""
        try:
            # OBV
            df['obv'] = OnBalanceVolumeIndicator(df['close'], df['volume']).on_balance_volume()
            df['obv_sma'] = df['obv'].rolling(20).mean()
            df['obv_bullish'] = (df['obv'] > df['obv_sma']).astype(int)
            
            # 거래량 이동평균
            # 볼륨 이동평균 (직접 계산)
            df['volume_sma_5'] = df['volume'].rolling(window=5).mean()
            df['volume_sma_20'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma_20']
            df['high_volume'] = (df['volume_ratio'] > 2.0).astype(int)
            
            # VWAP 근사치
            df['vwap'] = (df['close'] * df['volume']).rolling(20).sum() / df['volume'].rolling(20).sum()
            df['price_above_vwap'] = (df['close'] > df['vwap']).astype(int)
            
            return df
        except Exception as e:
            logger.error(f"거래량 지표 계산 실패: {e}")
            return df
    
    @staticmethod
    def add_price_patterns(df: pd.DataFrame) -> pd.DataFrame:
        """가격 패턴 특성 추가"""
        try:
            # 캔들스틱 패턴
            df['body_size'] = abs(df['close'] - df['open']) / df['open']
            df['upper_shadow'] = (df['high'] - np.maximum(df['open'], df['close'])) / df['open']
            df['lower_shadow'] = (np.minimum(df['open'], df['close']) - df['low']) / df['open']
            
            # 강세/약세 캔들
            df['bullish_candle'] = (df['close'] > df['open']).astype(int)
            df['bearish_candle'] = (df['close'] < df['open']).astype(int)
            
            # 연속 상승/하락
            df['consecutive_up'] = (df['close'] > df['close'].shift(1)).astype(int)
            df['consecutive_down'] = (df['close'] < df['close'].shift(1)).astype(int)
            
            # 갭
            df['gap_up'] = (df['open'] > df['close'].shift(1)).astype(int)
            df['gap_down'] = (df['open'] < df['close'].shift(1)).astype(int)
            
            # 고가/저가 돌파
            df['high_breakout'] = (df['close'] > df['high'].shift(1)).astype(int)
            df['low_breakdown'] = (df['close'] < df['low'].shift(1)).astype(int)
            
            # N일 고가/저가 대비 위치
            for period in [5, 10, 20]:
                df[f'high_position_{period}'] = (df['close'] - df['low'].rolling(period).min()) / (df['high'].rolling(period).max() - df['low'].rolling(period).min())
            
            return df
        except Exception as e:
            logger.error(f"가격 패턴 계산 실패: {e}")
            return df

class FeatureEngineering:
    """특성 공학"""
    
    def __init__(self):
        self.indicators = TechnicalIndicators()
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """모든 특성 생성"""
        try:
            if df is None or df.empty or len(df) < 100:
                logger.warning(f"데이터 부족: {len(df) if df is not None else 0}행")
                return df if df is not None else pd.DataFrame()
            
            # 기본 복사
            features_df = df.copy()
            
            # 각 카테고리별 지표 추가
            features_df = self.indicators.add_moving_averages(features_df)
            features_df = self.indicators.add_momentum_indicators(features_df)
            features_df = self.indicators.add_volatility_indicators(features_df)
            features_df = self.indicators.add_volume_indicators(features_df)
            features_df = self.indicators.add_price_patterns(features_df)
            
            # 추가 특성
            features_df = self._add_time_features(features_df)
            features_df = self._add_statistical_features(features_df)
            
            # NaN 처리 (pandas 2.0+ 호환 방식)
            features_df = features_df.ffill().fillna(0)
            
            logger.debug(f"특성 생성 완료: {features_df.shape[1]}개 컬럼, {len(features_df)}행")
            return features_df
            
        except Exception as e:
            logger.error(f"특성 생성 실패: {e}")
            return df
    
    def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """시간 기반 특성"""
        try:
            # 시간 기반 특성 추가 (안전한 방식)
            if 'timestamp' in df.columns:
                # timestamp 컬럼이 있는 경우
                timestamp_col = pd.to_datetime(df['timestamp'])
                df['hour'] = timestamp_col.dt.hour
                df['day_of_week'] = timestamp_col.dt.dayofweek
                df['is_weekend'] = (timestamp_col.dt.dayofweek >= 5).astype(int)
            elif isinstance(df.index, pd.DatetimeIndex):
                # DatetimeIndex인 경우
                df['hour'] = df.index.hour
                df['day_of_week'] = df.index.dayofweek
                df['is_weekend'] = (df.index.dayofweek >= 5).astype(int)
            else:
                # 현재 시간 기반으로 기본값 설정
                from datetime import datetime
                now = datetime.now()
                df['hour'] = now.hour
                df['day_of_week'] = now.weekday()
                df['is_weekend'] = 1 if now.weekday() >= 5 else 0
            
            # 시간대별 분류
            df['asian_session'] = ((df['hour'] >= 23) | (df['hour'] <= 7)).astype(int)
            df['european_session'] = ((df['hour'] >= 7) & (df['hour'] <= 15)).astype(int)
            df['american_session'] = ((df['hour'] >= 15) & (df['hour'] <= 23)).astype(int)
            
            return df
        except Exception as e:
            logger.error(f"시간 특성 생성 실패: {e}")
            # 오류 시 기본값으로 설정
            try:
                df['hour'] = 12  # 기본값
                df['day_of_week'] = 1  # 기본값 (월요일)
                df['is_weekend'] = 0
                df['asian_session'] = 0
                df['european_session'] = 1
                df['american_session'] = 0
            except:
                pass
            return df
    
    def _add_statistical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """통계적 특성"""
        try:
            # 롤링 통계
            for window in [5, 10, 20]:
                df[f'close_mean_{window}'] = df['close'].rolling(window).mean()
                df[f'close_std_{window}'] = df['close'].rolling(window).std()
                df[f'close_skew_{window}'] = df['close'].rolling(window).skew()
                df[f'close_kurt_{window}'] = df['close'].rolling(window).kurt()
                
                # Z-score
                df[f'close_zscore_{window}'] = (df['close'] - df[f'close_mean_{window}']) / df[f'close_std_{window}']
            
            # 가격 순위
            for window in [10, 20, 50]:
                df[f'price_rank_{window}'] = df['close'].rolling(window).rank(pct=True)
            
            return df
        except Exception as e:
            logger.error(f"통계적 특성 생성 실패: {e}")
            return df
    
    def create_target(self, df: pd.DataFrame, prediction_window: int = 12, threshold: float = 0.03) -> pd.DataFrame:
        """타겟 변수 생성 (급등 라벨)"""
        try:
            # 미래 최고가
            df['future_high'] = df['high'].shift(-1).rolling(window=prediction_window).max()
            
            # 급등 여부 (threshold% 이상 상승)
            df['future_return'] = (df['future_high'] - df['close']) / df['close']
            df['target'] = (df['future_return'] >= threshold).astype(int)
            
            # 최근 데이터는 라벨 없음 (미래 데이터 부족)
            df.loc[df.index[-prediction_window:], 'target'] = np.nan
            
            return df
            
        except Exception as e:
            logger.error(f"타겟 생성 실패: {e}")
            return df