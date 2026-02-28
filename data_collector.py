"""
다중 시간대 데이터 수집 모듈
5분, 15분, 1시간 봉 데이터 동시 수집 및 관리
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from loguru import logger
import asyncio
import aiohttp
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from binance_api import BinanceConnector
from utils import save_json, load_json, ensure_dir

class MultiTimeframeDataCollector:
    """다중 시간대 데이터 수집기"""
    
    def __init__(self, config, binance_connector: BinanceConnector):
        self.config = config
        self.binance = binance_connector
        
        # 다중 시간대 설정
        self.timeframes = ['5m', '15m', '1h']
        self.data_dir = ensure_dir("market_data")
        
        # 데이터 캐시
        self.data_cache = {}
        self.last_update = {}
        
        # 수집 통계
        self.collection_stats = {
            'total_symbols': 0,
            'successful_collections': 0,
            'failed_collections': 0,
            'last_full_update': None,
            'collection_time_seconds': 0
        }
        
        logger.info(f"📊 다중 시간대 데이터 수집기 초기화: {self.timeframes}")
    
    async def get_all_tradeable_symbols(self, min_volume: float = 300000) -> List[str]:
        """모든 거래 가능한 USDT 페어 조회"""
        try:
            logger.info("🔍 모든 USDT 페어 스캔 시작...")
            
            # 24시간 거래량 기준 필터링
            symbols = self.binance.get_usdt_pairs(min_volume=min_volume)
            
            # 안정성 필터 추가
            exclude_patterns = ['UP', 'DOWN', 'BULL', 'BEAR', '3L', '3S', '5L', '5S']
            filtered_symbols = []
            
            for symbol in symbols:
                # 제외 패턴 체크
                should_exclude = any(pattern in symbol for pattern in exclude_patterns)
                if not should_exclude:
                    filtered_symbols.append(symbol)
            
            self.collection_stats['total_symbols'] = len(filtered_symbols)
            logger.info(f"✅ 거래 대상 심볼: {len(filtered_symbols)}개")
            
            return filtered_symbols
            
        except Exception as e:
            logger.error(f"❌ 심볼 조회 실패: {e}")
            return []
    
    async def collect_symbol_data(self, symbol: str, timeframe: str, limit: int = 500) -> Optional[pd.DataFrame]:
        """개별 심볼의 특정 시간대 데이터 수집"""
        try:
            # 캐시 키 생성
            cache_key = f"{symbol}_{timeframe}"
            current_time = datetime.now()
            
            # 캐시된 데이터가 최신인지 확인 (5분 이내)
            if cache_key in self.data_cache and cache_key in self.last_update:
                time_diff = (current_time - self.last_update[cache_key]).total_seconds()
                if time_diff < 300:  # 5분
                    return self.data_cache[cache_key]
            
            # 새로운 데이터 수집
            df = self.binance.fetch_ohlcv(symbol, timeframe, limit)
            
            if df is not None and len(df) > 0:
                # 캐시 업데이트
                self.data_cache[cache_key] = df
                self.last_update[cache_key] = current_time
                
                return df
            else:
                logger.warning(f"⚠️ {symbol} {timeframe} 데이터 없음")
                return None
                
        except Exception as e:
            logger.warning(f"❌ {symbol} {timeframe} 수집 실패: {e}")
            return None
    
    async def collect_all_timeframes_for_symbol(self, symbol: str) -> Dict[str, pd.DataFrame]:
        """하나 심볼의 모든 시간대 데이터 수집"""
        symbol_data = {}
        
        for timeframe in self.timeframes:
            df = await self.collect_symbol_data(symbol, timeframe)
            if df is not None:
                symbol_data[timeframe] = df
        
        return symbol_data
    
    async def batch_collect_data(self, symbols: List[str], batch_size: int = 10) -> Dict[str, Dict[str, pd.DataFrame]]:
        """배치 단위로 다중 시간대 데이터 수집"""
        start_time = time.time()
        all_data = {}
        successful = 0
        failed = 0
        
        logger.info(f"📊 {len(symbols)}개 심볼 데이터 수집 시작...")
        
        # 배치 단위로 처리
        for i in range(0, len(symbols), batch_size):
            batch_symbols = symbols[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(symbols) + batch_size - 1) // batch_size
            
            logger.info(f"🔄 배치 {batch_num}/{total_batches} 처리 중... ({len(batch_symbols)}개 심볼)")
            
            # 동시 수집
            tasks = [self.collect_all_timeframes_for_symbol(symbol) for symbol in batch_symbols]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 결과 처리
            for symbol, result in zip(batch_symbols, batch_results):
                if isinstance(result, Exception):
                    logger.warning(f"❌ {symbol} 수집 실패: {result}")
                    failed += 1
                elif isinstance(result, dict) and len(result) > 0:
                    all_data[symbol] = result
                    successful += 1
                else:
                    failed += 1
            
            # API 제한 대응
            await asyncio.sleep(0.5)
        
        # 통계 업데이트
        collection_time = time.time() - start_time
        self.collection_stats.update({
            'successful_collections': successful,
            'failed_collections': failed,
            'last_full_update': datetime.now(),
            'collection_time_seconds': round(collection_time, 2)
        })
        
        success_rate = (successful / len(symbols)) * 100
        logger.info(f"✅ 데이터 수집 완료: {successful}/{len(symbols)} 성공 ({success_rate:.1f}%, {collection_time:.1f}초)")
        
        return all_data
    
    def save_collected_data(self, data: Dict[str, Dict[str, pd.DataFrame]], timestamp: Optional[str] = None) -> Optional[str]:
        """수집된 데이터 저장"""
        try:
            if timestamp is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            
            save_path = self.data_dir / f"market_data_{timestamp}.pkl"
            
            # 데이터프레임을 딕셔너리로 변환하여 저장
            serializable_data = {}
            for symbol, timeframe_data in data.items():
                serializable_data[symbol] = {}
                for timeframe, df in timeframe_data.items():
                    # CSV 형태로 저장
                    csv_path = self.data_dir / f"{symbol}_{timeframe}_{timestamp}.csv"
                    df.to_csv(csv_path, index=False)
                    serializable_data[symbol][timeframe] = str(csv_path)
            
            # 메타데이터 저장
            metadata = {
                'timestamp': timestamp,
                'total_symbols': len(data),
                'timeframes': self.timeframes,
                'collection_stats': self.collection_stats,
                'data_files': serializable_data
            }
            
            metadata_path = self.data_dir / f"metadata_{timestamp}.json"
            save_json(metadata, str(metadata_path))
            
            logger.info(f"💾 데이터 저장 완료: {len(data)}개 심볼 → {save_path}")
            return timestamp
            
        except Exception as e:
            logger.error(f"❌ 데이터 저장 실패: {e}")
            return None
    
    def load_latest_data(self) -> Optional[Dict[str, Dict[str, pd.DataFrame]]]:
        """최신 저장된 데이터 로드"""
        try:
            # 최신 메타데이터 찾기
            metadata_files = list(self.data_dir.glob("metadata_*.json"))
            if not metadata_files:
                return None
            
            latest_metadata_file = max(metadata_files, key=lambda x: x.stat().st_mtime)
            metadata = load_json(str(latest_metadata_file))
            
            # 데이터 파일 로드
            data = {}
            for symbol, timeframe_files in metadata['data_files'].items():
                data[symbol] = {}
                for timeframe, file_path in timeframe_files.items():
                    if Path(file_path).exists():
                        data[symbol][timeframe] = pd.read_csv(file_path, parse_dates=['timestamp'])
            
            logger.info(f"📂 최신 데이터 로드: {len(data)}개 심볼 ({metadata['timestamp']})")
            return data
            
        except Exception as e:
            logger.error(f"❌ 데이터 로드 실패: {e}")
            return None
    
    async def continuous_data_collection(self, symbols: List[str], update_interval: int = 300):
        """연속적인 데이터 수집 (5분마다)"""
        logger.info(f"🔄 연속 데이터 수집 시작: {update_interval}초 간격")
        
        while True:
            try:
                logger.info("📊 정기 데이터 업데이트 시작...")
                
                # 데이터 수집
                collected_data = await self.batch_collect_data(symbols)
                
                if collected_data:
                    # 저장
                    timestamp = self.save_collected_data(collected_data)
                    logger.info(f"✅ 정기 업데이트 완료: {timestamp}")
                else:
                    logger.warning("⚠️ 수집된 데이터 없음")
                
                # 다음 업데이트까지 대기
                await asyncio.sleep(update_interval)
                
            except Exception as e:
                logger.error(f"❌ 연속 수집 오류: {e}")
                await asyncio.sleep(60)  # 오류 시 1분 대기
    
    def get_collection_summary(self) -> Dict:
        """수집 현황 요약"""
        return {
            'timeframes': self.timeframes,
            'cache_size': len(self.data_cache),
            'stats': self.collection_stats,
            'data_directory': str(self.data_dir)
        }
    
    async def cleanup_old_data(self, days_to_keep: int = 7):
        """오래된 데이터 파일 정리"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # CSV 파일 정리
            csv_files = list(self.data_dir.glob("*.csv"))
            cleaned_count = 0
            
            for file_path in csv_files:
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_date:
                    file_path.unlink()
                    cleaned_count += 1
            
            logger.info(f"🧹 오래된 데이터 정리: {cleaned_count}개 파일 삭제")
            
        except Exception as e:
            logger.error(f"❌ 데이터 정리 실패: {e}")
