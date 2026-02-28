#!/usr/bin/env python3
"""
통합 ML 데이터셋 생성기 - 상승 추세 패턴 감지 특화
- 모든 거래 가능한 USDT 페어 스캔
- 기본 기술적 지표 + 상승 추세 특성
- 급등 패턴 라벨링 및 검증
- 다중 시간대 분석
- ML 모델 훈련용 고품질 데이터셋 생성
"""

import sys
import pandas as pd
import numpy as np
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger

# 로그 설정
logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}")
logger.add("logs/dataset_creation.log", rotation="100 MB", format="{time} | {level} | {message}")

# 경고 무시
warnings.filterwarnings('ignore')

from config import load_config
from binance_api import BinanceConnector
from data_collector import MultiTimeframeDataCollector
from features import FeatureEngineering
from ml_predictor import MLPredictor
from utils import save_json, load_json, ensure_dir

class AdvancedDatasetCreator:
    """고급 ML 데이터셋 생성기 - 상승 추세 패턴 특화"""
    
    def __init__(self, config_override: Optional[Dict] = None):
        """초기화"""
        self.config = load_config()
        if config_override:
            for key, value in config_override.items():
                setattr(self.config, key, value)
        
        # 컴포넌트 초기화
        self.binance = BinanceConnector(self.config)
        self.collector = MultiTimeframeDataCollector(self.config, self.binance)
        self.feature_eng = FeatureEngineering()
        self.ml_predictor = MLPredictor(self.config)
        
        # 데이터 저장 경로
        self.data_dir = ensure_dir("advanced_datasets")
        self.temp_dir = ensure_dir("temp_data")
        
        # 상승 추세 분석 설정
        self.trend_settings = {
            # 기본 필터링
            'min_volume_usdt': 10000,  # 최소 거래량을 낮춰서 더 많은 코인 포함
            'min_price_usdt': 0.0001,  # 최소 가격
            'max_symbols': 9999,  # 모든 USDT 심볼 포함 (제한 없음)
            
            # 추세 분석 기간
            'trend_periods': [3, 7, 14, 30],  # 단기~장기 추세
            'volume_periods': [7, 14, 30],    # 거래량 분석 기간
            
            # 급등 패턴 기준
            'surge_thresholds': {
                '1h': 0.05,   # 1시간 5% 이상
                '4h': 0.10,   # 4시간 10% 이상
                '1d': 0.20,   # 1일 20% 이상
                '7d': 0.50,   # 7일 50% 이상
            },
            
            # 거래량 급증 기준
            'volume_surge_multiplier': 2.0,  # 평균 대비 2배 이상
            
            # 돌파 패턴
            'breakout_threshold': 0.03,  # 3% 돌파
            'resistance_periods': [20, 50],  # 저항선 기간
            
            # 상승 지속성
            'momentum_periods': [5, 10, 20],  # 모멘텀 분석 기간
        }
        
        # 데이터 수집 통계
        self.collection_stats = {
            'total_symbols_scanned': 0,
            'successful_collections': 0,
            'failed_collections': 0,
            'trend_patterns_found': 0,
            'dataset_size': 0,
            'collection_start_time': None,
            'collection_end_time': None
        }
        
        logger.info("🚀 고급 ML 데이터셋 생성기 초기화 완료")
        logger.info(f"📊 설정 - 최소 거래량: ${self.trend_settings['min_volume_usdt']:,}")
        logger.info(f"🎯 최대 분석 심볼: {self.trend_settings['max_symbols']}개")
    
    async def discover_all_tradeable_pairs(self) -> List[str]:
        """거래 가능한 모든 USDT 페어 발견"""
        try:
            logger.info("🔍 거래 가능한 USDT 페어 전체 탐색 중...")
            
            # 기본 USDT 페어 조회
            pairs = self.binance.get_usdt_pairs(
                min_volume=self.trend_settings['min_volume_usdt']
            )
            
            if not pairs:
                logger.error("❌ USDT 페어를 찾을 수 없습니다")
                return []
            
            # 가격 필터링
            valid_pairs = []
            batch_size = 50
            
            for i in range(0, len(pairs), batch_size):
                batch = pairs[i:i + batch_size]
                
                for symbol in batch:
                    try:
                        current_price = self.binance.get_current_price(symbol)
                        if (current_price and 
                            current_price >= self.trend_settings['min_price_usdt']):
                            valid_pairs.append(symbol)
                    except Exception:
                        continue
                
                # API 제한 대응
                await asyncio.sleep(0.1)
            
            # 최대 심볼 수 제한
            if len(valid_pairs) > self.trend_settings['max_symbols']:
                valid_pairs = valid_pairs[:self.trend_settings['max_symbols']]
            
            logger.success(f"✅ 발견된 거래 가능 페어: {len(valid_pairs)}개")
            logger.info(f"상위 20개: {valid_pairs[:20]}")
            
            return valid_pairs
            
        except Exception as e:
            logger.error(f"❌ USDT 페어 탐색 실패: {e}")
            return []
    
    def create_advanced_trend_features(self, df: pd.DataFrame, symbol: str) -> Optional[pd.DataFrame]:
        """고급 상승 추세 특성 생성"""
        try:
            if len(df) < 100:  # 최소 데이터 요구사항
                return None
            
            # 기본 특성 생성 (기존 features.py 활용)
            features_df = self.feature_eng.create_features(df.copy())
            
            if features_df is None or len(features_df) < 50:
                return None
            
            # === 고급 상승 추세 특성 추가 ===
            
            # 1. 다기간 가격 변화율
            for period in self.trend_settings['trend_periods']:
                if len(features_df) > period:
                    features_df[f'price_change_{period}d'] = (
                        features_df['close'].pct_change(period).fillna(0)
                    )
                    features_df[f'high_change_{period}d'] = (
                        features_df['high'].pct_change(period).fillna(0)
                    )
            
            # 2. 거래량 기반 특성
            for period in self.trend_settings['volume_periods']:
                if len(features_df) > period:
                    vol_ma = features_df['volume'].rolling(period).mean()
                    features_df[f'volume_ratio_{period}d'] = (
                        features_df['volume'] / vol_ma
                    ).fillna(1.0)
                    
                    # 거래량 증가 추세
                    features_df[f'volume_trend_{period}d'] = (
                        features_df['volume'].rolling(period).apply(
                            lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) == period else 0
                        ).fillna(0)
                    )
            
            # 3. 가격 모멘텀 지표
            for period in self.trend_settings['momentum_periods']:
                if len(features_df) > period:
                    # ROC (Rate of Change)
                    features_df[f'roc_{period}'] = (
                        ((features_df['close'] / features_df['close'].shift(period)) - 1) * 100
                    ).fillna(0)
                    
                    # 모멘텀 강도
                    price_diff = features_df['close'].diff(period).fillna(0)
                    features_df[f'momentum_strength_{period}'] = np.abs(price_diff)
            
            # 4. 돌파 패턴 감지
            for period in self.trend_settings['resistance_periods']:
                if len(features_df) > period:
                    # 저항선/지지선
                    high_resistance = features_df['high'].rolling(period).max()
                    low_support = features_df['low'].rolling(period).min()
                    
                    # 돌파 신호
                    features_df[f'resistance_breakout_{period}'] = (
                        (features_df['close'] > high_resistance.shift(1)) & 
                        (features_df['close'].shift(1) <= high_resistance.shift(2))
                    ).astype(int)
                    
                    # 저항선 근접도
                    features_df[f'resistance_distance_{period}'] = (
                        (high_resistance - features_df['close']) / features_df['close']
                    ).fillna(0)
            
            # 5. 급등 패턴 라벨
            features_df = self.create_surge_labels(features_df)
            
            # 6. 추가 기술적 지표
            features_df = self.add_advanced_indicators(features_df)
            
            # 7. 시장 구조 특성
            features_df = self.add_market_structure_features(features_df)
            
            # 무한대 및 NaN 값 처리
            features_df = self.clean_features(features_df)
            
            return features_df
            
        except Exception as e:
            logger.warning(f"❌ {symbol} 고급 특성 생성 실패: {e}")
            return None
    
    def create_surge_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """급등 패턴 라벨 생성"""
        try:
            # 미래 수익률 계산 (다양한 기간)
            future_periods = [12, 24, 48, 168]  # 12시간, 1일, 2일, 7일 (5분봉 기준)
            
            for period in future_periods:
                if len(df) > period:
                    # 미래 최대 수익률
                    future_returns = []
                    for i in range(len(df) - period):
                        current_price = df['close'].iloc[i]
                        future_prices = df['high'].iloc[i+1:i+period+1]
                        if len(future_prices) > 0:
                            max_return = (future_prices.max() - current_price) / current_price
                            future_returns.append(max_return)
                        else:
                            future_returns.append(0)
                    
                    # 패딩
                    future_returns.extend([0] * period)
                    df[f'future_max_return_{period}h'] = future_returns
            
            # 메인 타겟 생성 - 24시간 내 10% 이상 상승
            if 'future_max_return_24h' in df.columns:
                df['surge_target'] = (df['future_max_return_24h'] >= 0.10).astype(int)
            else:
                df['surge_target'] = 0
            
            # 강도별 타겟
            thresholds = [0.05, 0.15, 0.25, 0.50]  # 5%, 15%, 25%, 50%
            for threshold in thresholds:
                if 'future_max_return_24h' in df.columns:
                    df[f'surge_{int(threshold*100)}pct'] = (
                        df['future_max_return_24h'] >= threshold
                    ).astype(int)
            
            return df
            
        except Exception as e:
            logger.warning(f"급등 라벨 생성 실패: {e}")
            return df
    
    def add_advanced_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """고급 기술적 지표 추가"""
        try:
            # Williams %R
            for period in [14, 21]:
                if len(df) > period:
                    high_max = df['high'].rolling(period).max()
                    low_min = df['low'].rolling(period).min()
                    df[f'williams_r_{period}'] = (
                        (high_max - df['close']) / (high_max - low_min) * -100
                    ).fillna(-50)
            
            # Commodity Channel Index (CCI)
            for period in [14, 20]:
                if len(df) > period:
                    tp = (df['high'] + df['low'] + df['close']) / 3
                    ma = tp.rolling(period).mean()
                    mad = tp.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean())
                    df[f'cci_{period}'] = ((tp - ma) / (0.015 * mad)).fillna(0)
            
            # Stochastic Oscillator
            for period in [14, 21]:
                if len(df) > period:
                    low_min = df['low'].rolling(period).min()
                    high_max = df['high'].rolling(period).max()
                    k_percent = 100 * (df['close'] - low_min) / (high_max - low_min)
                    df[f'stoch_k_{period}'] = k_percent.fillna(50)
                    df[f'stoch_d_{period}'] = k_percent.rolling(3).mean().fillna(50)
            
            # Average True Range (ATR) 기반 변동성
            for period in [14, 21]:
                if len(df) > period:
                    high_low = df['high'] - df['low']
                    high_close = np.abs(df['high'] - df['close'].shift(1))
                    low_close = np.abs(df['low'] - df['close'].shift(1))
                    
                    tr = np.maximum(high_low, np.maximum(high_close, low_close))
                    atr = pd.Series(tr).rolling(period).mean()
                    
                    df[f'atr_{period}'] = atr.fillna(0)
                    df[f'atr_ratio_{period}'] = (atr / df['close']).fillna(0)
            
            return df
            
        except Exception as e:
            logger.warning(f"고급 지표 생성 실패: {e}")
            return df
    
    def add_market_structure_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """시장 구조 특성 추가"""
        try:
            # Higher Highs, Higher Lows 패턴
            for period in [5, 10, 20]:
                if len(df) > period * 2:
                    # Higher Highs
                    hh = (df['high'] > df['high'].shift(period)).astype(int)
                    df[f'higher_highs_{period}'] = hh.rolling(period).sum()
                    
                    # Higher Lows
                    hl = (df['low'] > df['low'].shift(period)).astype(int)
                    df[f'higher_lows_{period}'] = hl.rolling(period).sum()
                    
                    # 상승 구조 점수
                    df[f'uptrend_structure_{period}'] = (
                        df[f'higher_highs_{period}'] + df[f'higher_lows_{period}']
                    ) / (period * 2)
            
            # 가격 패턴 분석
            if len(df) > 10:
                # 연속 상승/하락 일수
                price_direction = (df['close'] > df['close'].shift(1)).astype(int)
                
                up_streak = []
                down_streak = []
                current_up = 0
                current_down = 0
                
                for direction in price_direction:
                    if direction == 1:
                        current_up += 1
                        current_down = 0
                    else:
                        current_down += 1
                        current_up = 0
                    
                    up_streak.append(current_up)
                    down_streak.append(current_down)
                
                df['consecutive_ups'] = up_streak
                df['consecutive_downs'] = down_streak
            
            # 거래량-가격 관계
            if len(df) > 5:
                volume_ma = df['volume'].rolling(20).mean()
                price_change = df['close'].pct_change()
                volume_change = df['volume'] / volume_ma
                
                # 상승시 거래량 증가 패턴
                df['volume_price_correlation'] = (
                    (price_change > 0) & (volume_change > 1.5)
                ).astype(int)
            
            return df
            
        except Exception as e:
            logger.warning(f"시장 구조 특성 생성 실패: {e}")
            return df
    
    def clean_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """특성 데이터 정리"""
        try:
            # 무한대 값 처리
            df = df.replace([np.inf, -np.inf], np.nan)
            
            # NaN 값을 적절한 기본값으로 대체
            for col in df.columns:
                if df[col].dtype in ['float64', 'int64']:
                    if 'ratio' in col or 'pct' in col:
                        df[col] = df[col].fillna(0)
                    elif 'ma' in col or 'sma' in col or 'ema' in col:
                        df[col] = df[col].fillna(df['close'].mean())
                    elif 'rsi' in col:
                        df[col] = df[col].fillna(50)
                    elif 'williams' in col:
                        df[col] = df[col].fillna(-50)
                    elif 'stoch' in col:
                        df[col] = df[col].fillna(50)
                    else:
                        df[col] = df[col].fillna(0)
            
            # 극값 처리 (3 시그마 규칙)
            for col in df.select_dtypes(include=[np.number]).columns:
                if col not in ['open', 'high', 'low', 'close', 'volume']:
                    mean = df[col].mean()
                    std = df[col].std()
                    
                    if std > 0:
                        lower_bound = mean - 3 * std
                        upper_bound = mean + 3 * std
                        df[col] = df[col].clip(lower_bound, upper_bound)
            
            return df
            
        except Exception as e:
            logger.warning(f"특성 정리 실패: {e}")
            return df
    
    async def collect_symbol_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """개별 심볼 데이터 수집 및 특성 생성"""
        try:
            logger.debug(f"📊 {symbol} 데이터 수집 중...")
            
            # 5분봉 데이터 수집 (더 많은 데이터)
            raw_data = self.binance.fetch_ohlcv(symbol, '5m', limit=1000)
            
            if raw_data is None or len(raw_data) < 200:
                logger.warning(f"❌ {symbol}: 데이터 부족 ({len(raw_data) if raw_data is not None else 0}행)")
                return None
            
            # 고급 특성 생성
            features_df = self.create_advanced_trend_features(raw_data, symbol)
            
            if features_df is None or len(features_df) < 100:
                logger.warning(f"❌ {symbol}: 특성 생성 실패")
                return None
            
            # 심볼 정보 추가
            features_df['symbol'] = symbol
            features_df['timestamp'] = datetime.now()
            
            # 급등 패턴 발견 확인
            if 'surge_target' in features_df.columns:
                surge_count = features_df['surge_target'].sum()
                if surge_count > 0:
                    self.collection_stats['trend_patterns_found'] += surge_count
                    logger.success(f"🎯 {symbol}: {surge_count}개 급등 패턴 발견")
            
            logger.debug(f"✅ {symbol}: {len(features_df)}행, {len(features_df.columns)}개 특성")
            return features_df
            
        except Exception as e:
            logger.warning(f"❌ {symbol} 데이터 수집 실패: {e}")
            return None
    
    async def create_comprehensive_dataset(self, symbols: Optional[List[str]] = None, 
                                         batch_size: int = 20) -> pd.DataFrame:
        """종합 데이터셋 생성"""
        try:
            self.collection_stats['collection_start_time'] = datetime.now()
            
            # 심볼 목록 준비
            if symbols is None:
                symbols = await self.discover_all_tradeable_pairs()
            
            if not symbols:
                logger.error("❌ 분석할 심볼이 없습니다")
                return pd.DataFrame()
            
            self.collection_stats['total_symbols_scanned'] = len(symbols)
            logger.info(f"🎯 대상 심볼: {len(symbols)}개")
            
            # 배치별 데이터 수집
            all_features = []
            failed_symbols = []
            
            for i in range(0, len(symbols), batch_size):
                batch_symbols = symbols[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(symbols) + batch_size - 1) // batch_size
                
                logger.info(f"📦 배치 {batch_num}/{total_batches} 처리 중... ({len(batch_symbols)}개 심볼)")
                
                # 배치 내 병렬 처리
                tasks = [self.collect_symbol_data(symbol) for symbol in batch_symbols]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for symbol, result in zip(batch_symbols, batch_results):
                    if isinstance(result, Exception):
                        logger.warning(f"❌ {symbol}: {result}")
                        failed_symbols.append(symbol)
                        self.collection_stats['failed_collections'] += 1
                    elif result is not None:
                        all_features.append(result)
                        self.collection_stats['successful_collections'] += 1
                    else:
                        failed_symbols.append(symbol)
                        self.collection_stats['failed_collections'] += 1
                
                # API 제한 대응
                await asyncio.sleep(1)
                
                # 중간 진행 상황
                success_rate = (self.collection_stats['successful_collections'] / 
                              (self.collection_stats['successful_collections'] + 
                               self.collection_stats['failed_collections']) * 100)
                logger.info(f"📊 진행률: {success_rate:.1f}% "
                          f"(성공: {self.collection_stats['successful_collections']}, "
                          f"실패: {self.collection_stats['failed_collections']})")
            
            if not all_features:
                logger.error("❌ 수집된 데이터가 없습니다")
                return pd.DataFrame()
            
            # 데이터프레임 결합
            logger.info("🔄 데이터 결합 중...")
            final_dataset = pd.concat(all_features, ignore_index=True)
            
            # 최종 정리
            final_dataset = self.finalize_dataset(final_dataset)
            
            self.collection_stats['collection_end_time'] = datetime.now()
            self.collection_stats['dataset_size'] = len(final_dataset)
            
            # 통계 출력
            self.print_collection_summary(final_dataset, failed_symbols)
            
            return final_dataset
            
        except Exception as e:
            logger.error(f"❌ 데이터셋 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def finalize_dataset(self, df: pd.DataFrame) -> pd.DataFrame:
        """데이터셋 최종 정리"""
        try:
            logger.info("🔧 데이터셋 최종 정리 중...")
            
            # 중복 제거
            before_size = len(df)
            df = df.drop_duplicates()
            after_size = len(df)
            
            if before_size != after_size:
                logger.info(f"📊 중복 제거: {before_size} → {after_size}행")
            
            # 결측값 처리
            null_counts = df.isnull().sum()
            high_null_columns = null_counts[null_counts > len(df) * 0.5].index
            
            if len(high_null_columns) > 0:
                logger.warning(f"⚠️ 높은 결측률 컬럼 제거: {list(high_null_columns)}")
                df = df.drop(columns=high_null_columns)
            
            # 남은 결측값 처리
            for col in df.select_dtypes(include=[np.number]).columns:
                if df[col].isnull().any():
                    df[col] = df[col].fillna(df[col].median())
            
            # 타겟 분포 확인
            if 'surge_target' in df.columns:
                target_dist = df['surge_target'].value_counts()
                total = len(df)
                logger.info(f"🎯 타겟 분포:")
                logger.info(f"   급등 패턴(1): {target_dist.get(1, 0):,}개 ({target_dist.get(1, 0)/total*100:.1f}%)")
                logger.info(f"   일반 패턴(0): {target_dist.get(0, 0):,}개 ({target_dist.get(0, 0)/total*100:.1f}%)")
            
            # 컬럼 순서 정리
            feature_columns = [col for col in df.columns if col not in 
                             ['symbol', 'timestamp', 'surge_target'] + 
                             [col for col in df.columns if 'future_' in col or 'surge_' in col]]
            
            target_columns = [col for col in df.columns if 'surge_' in col or col == 'surge_target']
            meta_columns = ['symbol', 'timestamp']
            
            final_columns = meta_columns + feature_columns + target_columns
            df = df[[col for col in final_columns if col in df.columns]]
            
            return df
            
        except Exception as e:
            logger.warning(f"데이터셋 정리 실패: {e}")
            return df
    
    def print_collection_summary(self, dataset: pd.DataFrame, failed_symbols: List[str]):
        """수집 결과 요약 출력"""
        duration = (self.collection_stats['collection_end_time'] - 
                   self.collection_stats['collection_start_time'])
        
        logger.info("\n" + "="*80)
        logger.info("📊 데이터셋 생성 완료 요약")
        logger.info("="*80)
        
        logger.info(f"⏱️ 소요 시간: {duration}")
        logger.info(f"📈 스캔된 심볼: {self.collection_stats['total_symbols_scanned']}개")
        logger.info(f"✅ 성공한 수집: {self.collection_stats['successful_collections']}개")
        logger.info(f"❌ 실패한 수집: {self.collection_stats['failed_collections']}개")
        logger.info(f"🎯 발견된 급등 패턴: {self.collection_stats['trend_patterns_found']}개")
        
        if len(dataset) > 0:
            logger.info(f"📊 최종 데이터셋 크기: {len(dataset):,}행 x {len(dataset.columns)}컬럼")
            logger.info(f"💾 예상 파일 크기: ~{len(dataset) * len(dataset.columns) * 8 / 1024 / 1024:.1f} MB")
            
            # 심볼별 통계
            if 'symbol' in dataset.columns:
                symbol_counts = dataset['symbol'].value_counts()
                logger.info(f"📈 심볼별 평균 데이터: {symbol_counts.mean():.0f}행")
                logger.info(f"   최대: {symbol_counts.max()}행, 최소: {symbol_counts.min()}행")
        
        if failed_symbols:
            logger.warning(f"⚠️ 실패한 심볼 예시 (상위 10개): {failed_symbols[:10]}")
        
        logger.info("="*80)
    
    async def save_dataset(self, dataset: pd.DataFrame, suffix: str = "") -> str:
        """데이터셋 저장"""
        try:
            if len(dataset) == 0:
                logger.error("❌ 저장할 데이터가 없습니다")
                return ""
            
            # 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"advanced_trend_dataset_{timestamp}{suffix}.csv"
            filepath = self.data_dir / filename
            
            # CSV 저장
            dataset.to_csv(filepath, index=False)
            file_size = filepath.stat().st_size / 1024 / 1024  # MB
            
            logger.success(f"💾 데이터셋 저장 완료: {filepath}")
            logger.info(f"   파일 크기: {file_size:.1f} MB")
            
            # 메타데이터 저장
            metadata = {
                'creation_time': datetime.now().isoformat(),
                'dataset_size': len(dataset),
                'feature_count': len(dataset.columns),
                'collection_stats': self.collection_stats,
                'trend_settings': self.trend_settings,
                'file_path': str(filepath),
                'file_size_mb': file_size
            }
            
            metadata_path = filepath.with_suffix('.json')
            save_json(metadata, str(metadata_path))
            
            return str(filepath)
            
        except Exception as e:
            logger.error(f"❌ 데이터셋 저장 실패: {e}")
            return ""
    
    async def run_comprehensive_analysis(self, max_symbols: Optional[int] = None) -> str:
        """종합 분석 실행"""
        try:
            logger.info("🚀 종합 ML 데이터셋 생성 시작")
            
            # 최대 심볼 수 설정
            if max_symbols:
                self.trend_settings['max_symbols'] = max_symbols
            
            # 1. 심볼 발견
            symbols = await self.discover_all_tradeable_pairs()
            
            if not symbols:
                logger.error("❌ 분석할 심볼이 없습니다")
                return ""
            
            # 2. 데이터셋 생성
            dataset = await self.create_comprehensive_dataset(symbols)
            
            if len(dataset) == 0:
                logger.error("❌ 생성된 데이터셋이 비어있습니다")
                return ""
            
            # 3. 데이터셋 저장
            saved_path = await self.save_dataset(dataset, "_comprehensive")
            
            if saved_path:
                logger.success(f"🎉 종합 분석 완료! 데이터셋: {saved_path}")
            else:
                logger.error("❌ 데이터셋 저장 실패")
            
            return saved_path
            
        except Exception as e:
            logger.error(f"❌ 종합 분석 실패: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def validate_dataset_quality(self, dataset: pd.DataFrame) -> Dict[str, Any]:
        """데이터셋 품질 검증"""
        try:
            logger.info("🔍 데이터셋 품질 검증 중...")
            
            validation_results = {
                'basic_info': {
                    'total_rows': len(dataset),
                    'total_columns': len(dataset.columns),
                    'memory_usage_mb': dataset.memory_usage(deep=True).sum() / 1024 / 1024,
                    'symbols_count': dataset['symbol'].nunique() if 'symbol' in dataset.columns else 0
                },
                'data_quality': {
                    'missing_values': dataset.isnull().sum().sum(),
                    'duplicate_rows': dataset.duplicated().sum(),
                    'infinite_values': np.isinf(dataset.select_dtypes(include=[np.number])).sum().sum()
                },
                'target_analysis': {},
                'feature_analysis': {},
                'validation_status': 'unknown'
            }
            
            # 필수 컬럼 확인
            required_columns = ['close', 'volume', 'symbol']
            missing_required = [col for col in required_columns if col not in dataset.columns]
            
            if missing_required:
                logger.error(f"❌ 필수 컬럼 누락: {missing_required}")
                validation_results['validation_status'] = 'failed'
                validation_results['error'] = f"Missing required columns: {missing_required}"
                return validation_results
            
            # 타겟 분포 분석
            if 'surge_target' in dataset.columns:
                target_dist = dataset['surge_target'].value_counts()
                total = len(dataset)
                positive_rate = target_dist.get(1, 0) / total * 100 if total > 0 else 0
                
                validation_results['target_analysis'] = {
                    'negative_samples': target_dist.get(0, 0),
                    'positive_samples': target_dist.get(1, 0),
                    'positive_rate_percent': positive_rate,
                    'balance_status': 'good' if 5 <= positive_rate <= 40 else 'imbalanced'
                }
                
                logger.info(f"🎯 타겟 분포:")
                logger.info(f"   일반 패턴(0): {target_dist.get(0, 0):,}개 ({100-positive_rate:.1f}%)")
                logger.info(f"   급등 패턴(1): {target_dist.get(1, 0):,}개 ({positive_rate:.1f}%)")
                
                if 5 <= positive_rate <= 40:
                    logger.success("✅ 타겟 분포 적절")
                else:
                    logger.warning("⚠️ 타겟 분포 불균형 - 추가 데이터 수집 권장")
            
            # 특성 품질 분석
            numeric_columns = dataset.select_dtypes(include=[np.number]).columns
            feature_stats = {
                'numeric_features_count': len(numeric_columns),
                'high_variance_features': [],
                'low_variance_features': [],
                'correlated_features': []
            }
            
            # 분산 분석
            for col in numeric_columns:
                if col not in ['close', 'high', 'low', 'open', 'volume']:
                    variance = dataset[col].var()
                    if pd.notna(variance) and isinstance(variance, (int, float)):
                        if variance > 1000:
                            feature_stats['high_variance_features'].append(col)
                        elif variance < 0.001:
                            feature_stats['low_variance_features'].append(col)
            
            validation_results['feature_analysis'] = feature_stats
            
            # 전체 검증 상태 결정
            issues = []
            if validation_results['data_quality']['missing_values'] > len(dataset) * 0.1:
                issues.append("high_missing_values")
            if validation_results['data_quality']['duplicate_rows'] > len(dataset) * 0.05:
                issues.append("high_duplicates")
            if 'surge_target' in dataset.columns and validation_results['target_analysis']['balance_status'] == 'imbalanced':
                issues.append("target_imbalance")
            
            if not issues:
                validation_results['validation_status'] = 'excellent'
                logger.success("🏆 데이터셋 품질: 우수")
            elif len(issues) <= 1:
                validation_results['validation_status'] = 'good'
                logger.info("👍 데이터셋 품질: 양호")
            else:
                validation_results['validation_status'] = 'needs_improvement'
                logger.warning(f"⚠️ 데이터셋 품질 개선 필요: {issues}")
            
            validation_results['issues'] = issues
            
            logger.info("✅ 데이터셋 품질 검증 완료")
            return validation_results
            
        except Exception as e:
            logger.error(f"❌ 데이터셋 품질 검증 실패: {e}")
            return {
                'validation_status': 'error',
                'error': str(e)
            }
    
    async def load_and_validate_existing_dataset(self, filepath: Optional[str] = None) -> Optional[pd.DataFrame]:
        """기존 데이터셋 로드 및 검증"""
        try:
            if filepath is None:
                # 최신 데이터셋 파일 찾기
                dataset_files = list(self.data_dir.glob("*.csv"))
                if not dataset_files:
                    logger.warning("❌ 기존 데이터셋 파일이 없습니다")
                    return None
                
                # 가장 최근 파일 선택
                latest_file = max(dataset_files, key=lambda f: f.stat().st_mtime)
                filepath = str(latest_file)
            
            logger.info(f"📁 데이터셋 로드 중: {filepath}")
            
            # 파일 크기 확인
            file_size = Path(filepath).stat().st_size / 1024 / 1024
            logger.info(f"📊 파일 크기: {file_size:.1f} MB")
            
            # 데이터셋 로드
            dataset = pd.read_csv(filepath)
            logger.success(f"✅ 데이터셋 로드 완료: {len(dataset):,}행 x {len(dataset.columns)}컬럼")
            
            return dataset
            
        except Exception as e:
            logger.error(f"❌ 데이터셋 로드 실패: {e}")
            return None
    
    async def check_dataset_quality(self, dataset_path: Optional[str] = None) -> Dict[str, Any]:
        """데이터셋 품질 체크 (final_dataset_check.py 기능 통합)"""
        try:
            logger.info("🔍 데이터셋 품질 최종 검증")
            logger.info("="*50)
            
            # 데이터셋 로드
            dataset = await self.load_and_validate_existing_dataset(dataset_path)
            
            if dataset is None:
                return {'status': 'error', 'message': '데이터셋을 로드할 수 없습니다'}
            
            # 품질 검증 실행
            validation_results = self.validate_dataset_quality(dataset)
            
            # 상세 검증 추가
            check_results = {
                'file_info': {
                    'file_path': dataset_path or 'latest',
                    'file_size_mb': dataset.memory_usage(deep=True).sum() / 1024 / 1024,
                    'rows': len(dataset),
                    'columns': len(dataset.columns)
                },
                'validation': validation_results,
                'recommendations': []
            }
            
            # 결과 출력
            logger.info(f"📁 데이터셋: {len(dataset):,}행 x {len(dataset.columns)}컬럼")
            
            # 필수 컬럼 확인
            required_columns = ['close', 'volume']
            missing_cols = [col for col in required_columns if col not in dataset.columns]
            
            if missing_cols:
                logger.error(f"❌ 필수 컬럼 누락: {missing_cols}")
                check_results['recommendations'].append("필수 컬럼 추가 필요")
            else:
                logger.success("✅ 필수 컬럼 모두 존재")
            
            # 타겟 분포 확인
            if 'surge_target' in dataset.columns:
                target_dist = dataset['surge_target'].value_counts()
                total = len(dataset)
                pos_rate = target_dist.get(1, 0) / total * 100
                
                logger.info(f"🎯 타겟 분포:")
                logger.info(f"   일반 패턴(0): {target_dist.get(0, 0):,}개 ({100-pos_rate:.1f}%)")
                logger.info(f"   급등 패턴(1): {target_dist.get(1, 0):,}개 ({pos_rate:.1f}%)")
                
                if 5 <= pos_rate <= 40:
                    logger.success("✅ 타겟 분포 적절")
                else:
                    logger.warning("⚠️ 타겟 분포 불균형")
                    check_results['recommendations'].append("타겟 분포 조정 권장")
            
            # 특성 개수 확인
            feature_cols = [col for col in dataset.columns 
                           if col not in ['symbol', 'timestamp', 'surge_target']]
            logger.info(f"📊 특성 수: {len(feature_cols)}개")
            
            if len(feature_cols) >= 50:
                logger.success("✅ 충분한 특성 수")
            else:
                logger.warning("⚠️ 특성 수 부족할 수 있음")
                check_results['recommendations'].append("더 많은 특성 생성 권장")
            
            # 데이터 품질 확인
            null_count = dataset.isnull().sum().sum()
            null_rate = null_count / (len(dataset) * len(dataset.columns)) * 100
            logger.info(f"🔍 결측값: {null_count:,}개 ({null_rate:.2f}%)")
            
            if null_rate < 5:
                logger.success("✅ 데이터 품질 양호")
            else:
                logger.warning("⚠️ 결측값 많음")
                check_results['recommendations'].append("결측값 처리 필요")
            
            # 심볼 확인
            if 'symbol' in dataset.columns:
                unique_symbols = dataset['symbol'].nunique()
                logger.info(f"💰 포함된 심볼: {unique_symbols}개")
                
                if unique_symbols >= 10:
                    logger.success("✅ 다양한 심볼 포함")
                else:
                    logger.warning("⚠️ 심볼 다양성 부족")
                    check_results['recommendations'].append("더 많은 심볼 데이터 수집 권장")
            
            # 최종 결론
            logger.info("")
            logger.info("🎉 최종 결론:")
            
            if validation_results['validation_status'] in ['excellent', 'good']:
                logger.success("✅ 고품질 ML 훈련 데이터가 준비되어 있습니다!")
                logger.success("✅ 상승 추세 패턴 감지가 가능합니다!")
                logger.success("✅ 트레이딩 봇 실행 준비 완료!")
            else:
                logger.warning("⚠️ 데이터셋 품질 개선이 필요합니다")
                logger.info("권장 사항:")
                for rec in check_results['recommendations']:
                    logger.info(f"  • {rec}")
            
            logger.info("")
            logger.info("🚀 다음 단계:")
            logger.info("1. 데이터셋 생성: python advanced_dataset_creator.py create")
            logger.info("2. 모델 훈련: python train_production_model.py")
            logger.info("3. 페이퍼 트레이딩: python paper_main.py")
            logger.info("4. 대시보드 확인: python dashboard.py start")
            
            check_results['overall_status'] = validation_results['validation_status']
            return check_results
            
        except Exception as e:
            logger.error(f"❌ 품질 체크 실패: {e}")
            return {'status': 'error', 'message': str(e)}

    def generate_dataset_report(self, dataset: pd.DataFrame, validation_results: Dict[str, Any]) -> str:
        """데이터셋 분석 리포트 생성"""
        try:
            report_lines = [
                "📊 데이터셋 분석 리포트",
                "=" * 60,
                "",
                "🔢 기본 정보:",
                f"  • 총 데이터 행 수: {validation_results['basic_info']['total_rows']:,}개",
                f"  • 특성 컬럼 수: {validation_results['basic_info']['total_columns']}개",
                f"  • 메모리 사용량: {validation_results['basic_info']['memory_usage_mb']:.1f} MB",
                f"  • 분석 심볼 수: {validation_results['basic_info']['symbols_count']}개",
                "",
                "🔍 데이터 품질:",
                f"  • 결측값: {validation_results['data_quality']['missing_values']:,}개",
                f"  • 중복 행: {validation_results['data_quality']['duplicate_rows']:,}개",
                f"  • 무한값: {validation_results['data_quality']['infinite_values']:,}개",
                ""
            ]
            
            # 타겟 분석 추가
            if 'target_analysis' in validation_results and validation_results['target_analysis']:
                target_analysis = validation_results['target_analysis']
                report_lines.extend([
                    "🎯 타겟 분포:",
                    f"  • 일반 패턴: {target_analysis['negative_samples']:,}개",
                    f"  • 급등 패턴: {target_analysis['positive_samples']:,}개",
                    f"  • 급등 비율: {target_analysis['positive_rate_percent']:.1f}%",
                    f"  • 균형 상태: {target_analysis['balance_status']}",
                    ""
                ])
            
            # 특성 분석 추가
            if 'feature_analysis' in validation_results:
                feature_analysis = validation_results['feature_analysis']
                report_lines.extend([
                    "📈 특성 분석:",
                    f"  • 수치 특성 수: {feature_analysis['numeric_features_count']}개",
                    f"  • 고분산 특성: {len(feature_analysis['high_variance_features'])}개",
                    f"  • 저분산 특성: {len(feature_analysis['low_variance_features'])}개",
                    ""
                ])
            
            # 검증 상태
            status_emoji = {
                'excellent': '🏆',
                'good': '👍', 
                'needs_improvement': '⚠️',
                'failed': '❌',
                'error': '💥'
            }
            
            status = validation_results['validation_status']
            report_lines.extend([
                f"{status_emoji.get(status, '❓')} 전체 평가: {status}",
                ""
            ])
            
            if 'issues' in validation_results and validation_results['issues']:
                report_lines.extend([
                    "⚠️ 발견된 이슈:",
                    *[f"  • {issue}" for issue in validation_results['issues']],
                    ""
                ])
            
            report_lines.extend([
                "=" * 60,
                f"📅 생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ])
            
            return "\n".join(report_lines)
            
        except Exception as e:
            logger.error(f"❌ 리포트 생성 실패: {e}")
            return f"리포트 생성 중 오류 발생: {e}"

# === 메인 실행 함수들 ===

async def quick_test():
    """빠른 테스트 (소수 심볼)"""
    logger.info("🔬 빠른 테스트 모드")
    
    creator = AdvancedDatasetCreator({'max_symbols': 20})
    
    # 테스트용 심볼
    test_symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'ADA/USDT']
    
    dataset = await creator.create_comprehensive_dataset(test_symbols)
    
    if len(dataset) > 0:
        saved_path = await creator.save_dataset(dataset, "_quick_test")
        logger.success(f"✅ 빠른 테스트 완료: {saved_path}")
        return saved_path
    else:
        logger.error("❌ 빠른 테스트 실패")
        return ""

async def medium_analysis():
    """중간 규모 분석 (100개 심볼)"""
    logger.info("📊 중간 규모 분석")
    
    creator = AdvancedDatasetCreator({'max_symbols': 100})
    return await creator.run_comprehensive_analysis()

async def full_analysis():
    """전체 분석 (모든 USDT 심볼)"""
    logger.info("🌍 전체 시장 분석 - 모든 USDT 심볼")
    
    creator = AdvancedDatasetCreator({'max_symbols': 9999})  # 모든 심볼
    return await creator.run_comprehensive_analysis()

async def check_dataset():
    """기존 데이터셋 품질 체크"""
    logger.info("🔍 기존 데이터셋 품질 체크")
    
    creator = AdvancedDatasetCreator()
    result = await creator.check_dataset_quality()
    
    if result.get('status') == 'error':
        logger.error(f"❌ 체크 실패: {result.get('message', 'Unknown error')}")
    else:
        logger.success(f"✅ 품질 체크 완료: {result.get('overall_status', 'unknown')}")

async def main():
    """메인 실행 함수"""
    import sys
    
    logger.info("🚀 고급 ML 데이터셋 생성기")
    logger.info("="*50)
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
    else:
        command = "help"  # 기본값
    
    try:
        if command == "create":
            mode = sys.argv[2].lower() if len(sys.argv) > 2 else "medium"
            if mode == "quick":
                result = await quick_test()
            elif mode == "medium":
                result = await medium_analysis()
            elif mode == "full":
                result = await full_analysis()
            else:
                logger.error(f"❌ 알 수 없는 생성 모드: {mode}")
                logger.info("사용법: python advanced_dataset_creator.py create [quick|medium|full]")
                return
            
            if result:
                logger.success(f"🎉 데이터셋 생성 완료! 결과: {result}")
            else:
                logger.error("❌ 데이터셋 생성 실패")
        
        elif command == "check":
            await check_dataset()
        
        elif command == "validate":
            dataset_path = sys.argv[2] if len(sys.argv) > 2 else None
            creator = AdvancedDatasetCreator()
            result = await creator.check_dataset_quality(dataset_path)
            logger.success("✅ 검증 완료")
        
        elif command == "quick":
            result = await quick_test()
            if result:
                logger.success(f"✅ 빠른 테스트 완료: {result}")
        
        elif command == "help":
            logger.info("📖 사용법:")
            logger.info("")
            logger.info("🔧 데이터셋 생성:")
            logger.info("  python advanced_dataset_creator.py create quick   # 빠른 테스트 (5개 심볼)")
            logger.info("  python advanced_dataset_creator.py create medium # 중간 분석 (100개 심볼)")
            logger.info("  python advanced_dataset_creator.py create full   # 전체 분석 (500개 심볼)")
            logger.info("")
            logger.info("🔍 데이터셋 검증:")
            logger.info("  python advanced_dataset_creator.py check         # 최신 데이터셋 품질 체크")
            logger.info("  python advanced_dataset_creator.py validate [파일경로] # 특정 파일 검증")
            logger.info("")
            logger.info("⚡ 빠른 실행:")
            logger.info("  python advanced_dataset_creator.py quick         # 빠른 테스트")
            logger.info("  python advanced_dataset_creator.py help          # 도움말")
            logger.info("")
            logger.info("📊 예시:")
            logger.info("  python advanced_dataset_creator.py create medium")
            logger.info("  python advanced_dataset_creator.py check")
        
        else:
            logger.error(f"❌ 알 수 없는 명령어: {command}")
            logger.info("사용법: python advanced_dataset_creator.py help")
    
    except KeyboardInterrupt:
        logger.warning("⚠️ 사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"❌ 실행 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
