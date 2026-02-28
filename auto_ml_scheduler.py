#!/usr/bin/env python3
"""
자동 데이터셋 생성 및 ML 학습 스케줄러
매일 오전 9시와 오후 9시에 데이터셋 생성 후 ML 학습
"""

import asyncio
import schedule
import time
from datetime import datetime, timedelta
from loguru import logger
from pathlib import Path
import subprocess
import sys
import os
import pandas as pd

from config import load_config
from binance_api import BinanceConnector
from ml_predictor import MLPredictor
from telegram_notifier import TelegramNotifier
from utils import ensure_dir

class AutoMLScheduler:
    """자동 ML 데이터셋 생성 및 학습 스케줄러"""
    
    def __init__(self):
        self.config = load_config()
        self.binance = BinanceConnector(self.config)
        self.ml_predictor = MLPredictor(self.config)
        self.notifier = TelegramNotifier(
            self.config.TELEGRAM_BOT_TOKEN,
            self.config.TELEGRAM_CHAT_ID
        )
        
        # 디렉토리 생성
        ensure_dir("advanced_datasets")
        ensure_dir("models")
        ensure_dir("scheduler_logs")
        
        self.dataset_dir = Path("advanced_datasets")
        self.scheduler_logs_dir = Path("scheduler_logs")
        
        logger.info("🕘 자동 ML 스케줄러 초기화 완료")
    
    async def create_comprehensive_dataset(self):
        """포괄적 데이터셋 생성"""
        try:
            start_time = datetime.now()
            logger.info("📊 포괄적 데이터셋 생성 시작...")
            
            # 텔레그램 알림
            self.notifier.send_message("📊 자동 데이터셋 생성을 시작합니다...")
            
            # 상위 거래량 심볼 조회
            symbols = self.binance.get_usdt_pairs(min_volume=self.config.MIN_USDT_24H_VOLUME)
            if not symbols:
                raise Exception("거래 가능한 심볼을 찾을 수 없습니다")
            
            # 상위 100개 심볼 선택
            target_symbols = symbols[:100]
            logger.info(f"🎯 데이터셋 생성 대상: {len(target_symbols)}개 심볼")
            
            # 데이터 수집
            all_data = []
            timeframes = ['5m', '15m', '1h']
            days_back = 30
            
            for i, symbol in enumerate(target_symbols):
                try:
                    logger.info(f"📈 {symbol} 데이터 수집 중... ({i+1}/{len(target_symbols)})")
                    
                    for timeframe in timeframes:
                        # 데이터 가져오기
                        limit = min(1440 // {'5m': 5, '15m': 15, '1h': 60}[timeframe] * days_back, 1000)
                        df = self.binance.fetch_ohlcv(symbol, timeframe, limit)
                        
                        if df is None or len(df) < 100:
                            continue
                        
                        # 특성 생성
                        df_features = self.ml_predictor.feature_eng.create_features(df)
                        df_features = self.ml_predictor.feature_eng.create_target(
                            df_features, 
                            self.config.PREDICTION_WINDOW,
                            0.03  # 3% 급등 임계값
                        )
                        
                        # 메타데이터 추가
                        df_features['symbol'] = symbol
                        df_features['timeframe'] = timeframe
                        df_features['created_at'] = start_time.isoformat()
                        
                        all_data.append(df_features)
                        
                        # API 제한 방지
                        await asyncio.sleep(0.1)
                    
                    # 진행률 알림 (10개마다)
                    if (i + 1) % 10 == 0:
                        progress = (i + 1) / len(target_symbols) * 100
                        logger.info(f"📊 진행률: {progress:.1f}% ({i+1}/{len(target_symbols)})")
                
                except Exception as e:
                    logger.warning(f"❌ {symbol} 데이터 수집 실패: {e}")
                    continue
            
            if not all_data:
                raise Exception("수집된 데이터가 없습니다")
            
            # 데이터 결합 및 정리
            logger.info("🔄 데이터 결합 및 정리 중...")
            combined_df = pd.concat(all_data, ignore_index=True)
            combined_df = combined_df.dropna(subset=['target'])
            
            # 클래스 균형 조정
            surge_data = combined_df[combined_df['target'] == 1]
            normal_data = combined_df[combined_df['target'] == 0]
            
            if len(surge_data) > 0 and len(normal_data) > len(surge_data) * 3:
                # 정상 데이터를 급등 데이터의 3배로 제한
                normal_data = normal_data.sample(n=len(surge_data) * 3, random_state=42)
                combined_df = pd.concat([surge_data, normal_data], ignore_index=True)
                combined_df = combined_df.sample(frac=1, random_state=42).reset_index(drop=True)
            
            # 데이터셋 저장
            timestamp = start_time.strftime('%Y%m%d_%H%M')
            dataset_filename = f"comprehensive_dataset_{timestamp}.csv"
            dataset_path = self.dataset_dir / dataset_filename
            
            combined_df.to_csv(dataset_path, index=False)
            
            # 통계 정보
            total_rows = len(combined_df)
            surge_ratio = combined_df['target'].mean()
            unique_symbols = combined_df['symbol'].nunique()
            duration = (datetime.now() - start_time).total_seconds() / 60
            
            # 로그 기록
            log_data = {
                'timestamp': start_time.isoformat(),
                'dataset_file': dataset_filename,
                'total_rows': total_rows,
                'surge_ratio': surge_ratio,
                'unique_symbols': unique_symbols,
                'duration_minutes': duration,
                'status': 'completed'
            }
            
            log_path = self.scheduler_logs_dir / f"dataset_creation_{timestamp}.json"
            pd.Series(log_data).to_json(log_path)
            
            # 성공 알림
            message = f"""📊 자동 데이터셋 생성 완료!

📁 파일: {dataset_filename}
📈 총 데이터: {total_rows:,}행
💰 심볼: {unique_symbols}개
🎯 급등 비율: {surge_ratio:.2%}
⏱️ 소요시간: {duration:.1f}분

다음 단계: ML 모델 훈련이 시작됩니다..."""
            
            self.notifier.send_message(message)
            logger.info(f"✅ 데이터셋 생성 완료: {dataset_path}")
            
            return str(dataset_path)
            
        except Exception as e:
            error_msg = f"❌ 데이터셋 생성 실패: {e}"
            logger.error(error_msg)
            self.notifier.send_message(error_msg)
            return None
    
    async def train_ml_models(self, dataset_path: str):
        """ML 모델 훈련"""
        try:
            start_time = datetime.now()
            logger.info(f"🧠 ML 모델 훈련 시작: {dataset_path}")
            
            # 텔레그램 알림
            self.notifier.send_message("🧠 자동 ML 모델 훈련을 시작합니다...")
            
            # 데이터셋 로드
            df = pd.read_csv(dataset_path)
            logger.info(f"📊 훈련 데이터: {len(df):,}행, 급등 비율: {df['target'].mean():.2%}")
            
            # 모델 훈련 실행
            results = self.ml_predictor.train_models(df)
            
            if not results:
                raise Exception("모델 훈련 실패")
            
            # 최고 성능 모델 찾기
            best_model = max(results.keys(), key=lambda k: results[k].get('auc_score', 0))
            best_auc = results[best_model].get('auc_score', 0)
            
            # 모델 저장
            self.ml_predictor.save_models()
            
            duration = (datetime.now() - start_time).total_seconds() / 60
            
            # 성공 알림
            message = f"""🧠 자동 ML 모델 훈련 완료!

🏆 최고 성능: {best_model}
📊 AUC 점수: {best_auc:.3f}
🎯 모델 수: {len(results)}개
⏱️ 소요시간: {duration:.1f}분

✅ 새로운 모델이 활성화되었습니다!"""
            
            self.notifier.send_message(message)
            logger.info(f"✅ ML 모델 훈련 완료: {best_model} (AUC: {best_auc:.3f})")
            
            return True
            
        except Exception as e:
            error_msg = f"❌ ML 모델 훈련 실패: {e}"
            logger.error(error_msg)
            self.notifier.send_message(error_msg)
            return False
    
    async def run_scheduled_job(self):
        """스케줄된 작업 실행 (데이터셋 생성 + ML 훈련)"""
        try:
            job_start = datetime.now()
            logger.info("🕘 스케줄된 ML 작업 시작...")
            
            # 1단계: 데이터셋 생성
            dataset_path = await self.create_comprehensive_dataset()
            
            if not dataset_path:
                logger.error("❌ 데이터셋 생성 실패로 작업 중단")
                return
            
            # 2단계: ML 모델 훈련
            success = await self.train_ml_models(dataset_path)
            
            if not success:
                logger.error("❌ ML 모델 훈련 실패")
                return
            
            # 3단계: 완료 알림
            total_duration = (datetime.now() - job_start).total_seconds() / 60
            
            completion_message = f"""✅ 자동 ML 작업 완료!

📅 실행 시간: {job_start.strftime('%Y-%m-%d %H:%M:%S')}
⏱️ 총 소요시간: {total_duration:.1f}분
📊 데이터셋: 생성 완료
🧠 ML 모델: 훈련 완료

🎯 다음 스케줄: 매일 09:00, 21:00"""
            
            self.notifier.send_message(completion_message)
            logger.info("✅ 스케줄된 ML 작업 완료")
            
        except Exception as e:
            error_msg = f"❌ 스케줄된 ML 작업 실패: {e}"
            logger.error(error_msg)
            self.notifier.send_message(error_msg)
    
    def schedule_jobs(self):
        """작업 스케줄 설정"""
        def schedule_wrapper():
            """비동기 함수를 동기로 래핑"""
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.run_scheduled_job())
                loop.close()
            except Exception as e:
                logger.error(f"❌ 스케줄 작업 실행 오류: {e}")
        
        # 매일 오전 9시와 오후 9시에 실행
        schedule.every().day.at("09:00").do(schedule_wrapper)
        schedule.every().day.at("21:00").do(schedule_wrapper)
        
        logger.info("🕘 스케줄 설정 완료: 매일 09:00, 21:00에 자동 ML 작업 실행")
        
        # 시작 알림
        try:
            next_run_09 = schedule.jobs[0].next_run if schedule.jobs else None
            next_run_21 = schedule.jobs[1].next_run if len(schedule.jobs) > 1 else None
            
            next_runs = [run for run in [next_run_09, next_run_21] if run]
            next_run = min(next_runs) if next_runs else datetime.now() + timedelta(hours=1)
            
            message = f"""🕘 자동 ML 스케줄러 시작!

📅 실행 시간: 매일 09:00, 21:00
🔄 자동 작업:
  1. 포괄적 데이터셋 생성
  2. ML 모델 자동 훈련
  3. 새 모델 자동 활성화

⏰ 다음 실행: {next_run.strftime('%Y-%m-%d %H:%M:%S')}"""
            
            self.notifier.send_message(message)
        except Exception as e:
            logger.warning(f"⚠️ 시작 알림 전송 실패: {e}")
    
    def run(self):
        """스케줄러 메인 실행"""
        try:
            # 스케줄 설정
            self.schedule_jobs()
            
            # 스케줄러 실행
            logger.info("🔄 스케줄러 실행 중... (Ctrl+C로 종료)")
            while True:
                schedule.run_pending()
                time.sleep(60)  # 1분마다 체크
                
        except Exception as e:
            logger.error(f"❌ 스케줄러 실행 오류: {e}")
            self.notifier.send_message(f"❌ ML 스케줄러 오류: {e}")

async def main():
    """메인 함수"""
    logger.info("🚀 자동 ML 스케줄러 시작...")
    
    scheduler = AutoMLScheduler()
    
    try:
        # 즉시 테스트 실행 옵션
        if len(sys.argv) > 1 and sys.argv[1] == "--test":
            logger.info("🧪 테스트 모드: 즉시 실행")
            await scheduler.run_scheduled_job()
        elif len(sys.argv) > 1 and sys.argv[1] == "--daemon":
            logger.info("🔄 데몬 모드: 백그라운드 스케줄러 실행")
            scheduler.run()
        else:
            # 정규 스케줄 모드 (동기 실행)
            scheduler.run()
            
    except KeyboardInterrupt:
        logger.info("👋 스케줄러 종료")
    except Exception as e:
        logger.error(f"❌ 실행 오류: {e}")

def main_sync():
    """동기 메인 함수"""
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "--test":
            # 테스트 모드는 비동기로 실행
            asyncio.run(main())
        else:
            # 정규 모드는 동기로 실행
            scheduler = AutoMLScheduler()
            scheduler.run()
    except Exception as e:
        logger.error(f"❌ 실행 오류: {e}")

if __name__ == "__main__":
    main_sync()
