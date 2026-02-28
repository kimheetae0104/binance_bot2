#!/usr/bin/env python3
"""
🚀 통합 스케줄링 시스템 (UNIFIED SCHEDULER)
완전 자동화된 데이터 수집, 모델 훈련, 시스템 관리
"""

import schedule
import threading
import time
import subprocess
import sys
import signal
import json
import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from loguru import logger

from config import load_config
from binance_api import BinanceConnector
from telegram_notifier import TelegramNotifier
from utils import save_json, load_json, ensure_dir


class AutoSchedulingSystem:
    """완전 자동 스케줄링 시스템 - 24/7 운영"""
    
    def __init__(self):
        """초기화"""
        self.config = load_config()
        self.is_running = False
        self.schedule_thread = None
        
        # 컴포넌트
        self.binance = BinanceConnector(self.config)
        self.notifier = TelegramNotifier(
            self.config.TELEGRAM_BOT_TOKEN,
            self.config.TELEGRAM_CHAT_ID
        )
        
        # 상태 정보
        self.last_dataset_creation = None
        self.last_model_training = None
        self.task_history = []
        
        # 디렉토리
        self.log_dir = ensure_dir("scheduler_logs")
        
        logger.info("🚀 자동 스케줄링 시스템 초기화 완료")
        
    def start_scheduler(self):
        """스케줄러 시작"""
        if self.is_running:
            logger.warning("이미 실행 중입니다")
            return
            
        self.is_running = True
        self.setup_schedules()
        
        # 백그라운드 스레드 시작
        self.schedule_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.schedule_thread.start()
        
        logger.info("✅ 스케줄러 시작됨")
        self.send_notification("🚀 자동 스케줄링 시스템 시작")
        
    def setup_schedules(self):
        """스케줄 설정"""
        # 매일 오전 9시, 오후 9시: 데이터셋 + 모델 훈련
        schedule.every().day.at("09:00").do(self.run_full_update)
        schedule.every().day.at("21:00").do(self.run_full_update)
        
        # 매일 오전 6시: 시스템 상태 체크
        schedule.every().day.at("06:00").do(self.system_health_check)
        
        # 매주 일요일 오전 3시: 시스템 최적화
        schedule.every().sunday.at("03:00").do(self.weekly_optimization)
        
        logger.info("📅 스케줄 설정 완료")
        
    def _run_loop(self):
        """스케줄러 실행 루프"""
        while self.is_running:
            schedule.run_pending()
            time.sleep(60)  # 1분마다 체크
            
    def run_full_update(self):
        """전체 업데이트: 데이터셋 생성 + 모델 훈련"""
        try:
            logger.info("🔄 전체 업데이트 시작")
            start_time = time.time()
            
            # 1. 데이터셋 생성
            if self.create_dataset():
                # 2. 모델 훈련
                if self.train_model():
                    duration = time.time() - start_time
                    msg = f"✅ 전체 업데이트 완료 ({duration:.1f}초)"
                    logger.info(msg)
                    self.send_notification(msg)
                    self.record_task('full_update', True, duration)
                else:
                    self.send_notification("❌ 모델 훈련 실패")
                    self.record_task('full_update', False)
            else:
                self.send_notification("❌ 데이터셋 생성 실패")
                self.record_task('full_update', False)
                
        except Exception as e:
            msg = f"❌ 전체 업데이트 오류: {e}"
            logger.error(msg)
            self.send_notification(msg)
            self.record_task('full_update', False)
            
    def create_dataset(self):
        """데이터셋 생성"""
        try:
            logger.info("📊 데이터셋 생성 시작")
            
            result = subprocess.run([
                'python', 'advanced_dataset_creator.py'
            ], capture_output=True, text=True, timeout=3600)
            
            if result.returncode == 0:
                logger.info("✅ 데이터셋 생성 완료")
                self.last_dataset_creation = datetime.now()
                return True
            else:
                logger.error(f"❌ 데이터셋 생성 실패: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ 데이터셋 생성 시간 초과")
            return False
        except Exception as e:
            logger.error(f"❌ 데이터셋 생성 오류: {e}")
            return False
            
    def train_model(self):
        """ML 모델 훈련"""
        try:
            logger.info("🤖 ML 모델 훈련 시작")
            
            result = subprocess.run([
                'python', 'train_production_model.py'
            ], capture_output=True, text=True, timeout=7200)
            
            if result.returncode == 0:
                logger.info("✅ ML 모델 훈련 완료")
                self.last_model_training = datetime.now()
                return True
            else:
                logger.error(f"❌ ML 모델 훈련 실패: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ ML 모델 훈련 시간 초과")
            return False
        except Exception as e:
            logger.error(f"❌ ML 모델 훈련 오류: {e}")
            return False
            
    def system_health_check(self):
        """시스템 상태 체크"""
        try:
            logger.info("🔍 시스템 상태 체크 시작")
            
            status = {
                'timestamp': datetime.now().isoformat(),
                'dataset_files': self.check_dataset_files(),
                'model_files': self.check_model_files(),
                'config_status': self.check_config(),
                'disk_space': self.check_disk_space(),
                'last_dataset': self.last_dataset_creation.isoformat() if self.last_dataset_creation else None,
                'last_training': self.last_model_training.isoformat() if self.last_model_training else None
            }
            
            # 상태 저장
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            status_file = os.path.join(self.log_dir, f"health_{timestamp}.json")
            save_json(status, status_file)
            
            # 알림 발송
            msg = self.format_health_status(status)
            self.send_notification(f"🔍 시스템 상태\n{msg}")
            
            logger.info("✅ 시스템 상태 체크 완료")
            
        except Exception as e:
            msg = f"❌ 시스템 상태 체크 오류: {e}"
            logger.error(msg)
            self.send_notification(msg)
            
    def weekly_optimization(self):
        """주간 시스템 최적화"""
        try:
            logger.info("🔧 주간 최적화 시작")
            
            # 오래된 파일 정리
            log_cleaned = self.cleanup_old_files(self.log_dir, days=7)
            backup_cleaned = self.cleanup_old_files("backup_files", days=30)
            temp_cleaned = self.cleanup_temp_files()
            
            # 성능 리포트
            report = self.generate_performance_report()
            
            msg = f"✅ 주간 최적화 완료\n로그: {log_cleaned}개, 백업: {backup_cleaned}개, 임시: {temp_cleaned}개 정리\n\n{report}"
            logger.info(msg)
            self.send_notification(msg)
            
        except Exception as e:
            msg = f"❌ 주간 최적화 오류: {e}"
            logger.error(msg)
            self.send_notification(msg)
            
    def check_dataset_files(self):
        """데이터셋 파일 상태"""
        dataset_dir = "advanced_datasets"
        if not os.path.exists(dataset_dir):
            return {"status": "❌ 없음", "count": 0}
            
        files = [f for f in os.listdir(dataset_dir) if f.endswith('.csv')]
        return {
            "status": "✅ 정상" if files else "⚠️ 없음",
            "count": len(files),
            "latest": max(files, default=None, key=lambda x: os.path.getmtime(os.path.join(dataset_dir, x)))
        }
        
    def check_model_files(self):
        """모델 파일 상태"""
        model_dir = "models"
        if not os.path.exists(model_dir):
            return {"status": "❌ 없음", "count": 0}
            
        files = [f for f in os.listdir(model_dir) if f.endswith('.pkl')]
        return {
            "status": "✅ 정상" if files else "⚠️ 없음",
            "count": len(files),
            "latest": max(files, default=None, key=lambda x: os.path.getmtime(os.path.join(model_dir, x)))
        }
        
    def check_config(self):
        """설정 파일 상태"""
        try:
            config = load_config()
            required = ['API_KEY', 'API_SECRET', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']
            missing = [field for field in required if not hasattr(config, field) or not getattr(config, field)]
            
            return {
                "status": "✅ 정상" if not missing else "⚠️ 누락",
                "missing": missing
            }
        except Exception as e:
            return {"status": "❌ 오류", "error": str(e)}
            
    def check_disk_space(self):
        """디스크 공간 체크"""
        try:
            total, used, free = shutil.disk_usage(".")
            free_gb = free // (1024**3)
            usage_pct = (used / total) * 100
            
            if free_gb > 5:
                status = "✅ 충분"
            elif free_gb > 1:
                status = "⚠️ 부족"
            else:
                status = "❌ 매우부족"
                
            return {
                "status": status,
                "free_gb": free_gb,
                "usage_percent": round(usage_pct, 1)
            }
        except Exception as e:
            return {"status": "❌ 체크실패", "error": str(e)}
            
    def format_health_status(self, status):
        """상태 정보 포맷팅"""
        ds = status['dataset_files']
        model = status['model_files']
        config = status['config_status']
        disk = status['disk_space']
        
        lines = [
            f"📊 데이터셋: {ds['status']} ({ds['count']}개)",
            f"🤖 모델: {model['status']} ({model['count']}개)",
            f"⚙️ 설정: {config['status']}",
            f"💾 디스크: {disk['status']} ({disk['free_gb']}GB)"
        ]
        
        if status['last_dataset']:
            dt = datetime.fromisoformat(status['last_dataset'])
            lines.append(f"📅 마지막 데이터셋: {dt.strftime('%m/%d %H:%M')}")
            
        if status['last_training']:
            dt = datetime.fromisoformat(status['last_training'])
            lines.append(f"🕒 마지막 훈련: {dt.strftime('%m/%d %H:%M')}")
            
        return "\\n".join(lines)
        
    def cleanup_old_files(self, directory, days=7):
        """오래된 파일 정리"""
        if not os.path.exists(directory):
            return 0
            
        cutoff = datetime.now() - timedelta(days=days)
        cleaned = 0
        
        for root, _, files in os.walk(directory):
            for file in files:
                filepath = os.path.join(root, file)
                if os.path.getmtime(filepath) < cutoff.timestamp():
                    try:
                        os.remove(filepath)
                        cleaned += 1
                    except Exception:
                        pass
                        
        return cleaned
        
    def cleanup_temp_files(self):
        """임시 파일 정리"""
        temp_exts = ['.tmp', '.temp', '.cache', '.log']
        cleaned = 0
        
        for root, _, files in os.walk("."):
            for file in files:
                if any(file.endswith(ext) for ext in temp_exts):
                    filepath = os.path.join(root, file)
                    try:
                        os.remove(filepath)
                        cleaned += 1
                    except Exception:
                        pass
                        
        return cleaned
        
    def generate_performance_report(self):
        """성능 리포트 생성"""
        recent = [t for t in self.task_history 
                 if t['timestamp'] > datetime.now() - timedelta(days=7)]
        
        if not recent:
            return "📈 최근 작업 기록 없음"
            
        success_count = sum(1 for t in recent if t['success'])
        success_rate = (success_count / len(recent)) * 100
        avg_duration = sum(t.get('duration', 0) for t in recent if t['success']) / max(success_count, 1)
        
        return f"📈 최근 7일\\n성공률: {success_rate:.1f}% ({success_count}/{len(recent)})\\n평균 소요: {avg_duration:.1f}초"
        
    def record_task(self, task_type, success, duration=None):
        """작업 기록"""
        record = {
            'timestamp': datetime.now(),
            'task_type': task_type,
            'success': success,
            'duration': duration
        }
        
        self.task_history.append(record)
        
        # 최근 100개만 유지
        if len(self.task_history) > 100:
            self.task_history = self.task_history[-100:]
            
        # 파일 저장
        history_file = os.path.join(self.log_dir, "task_history.json")
        serializable = []
        for task in self.task_history:
            task_copy = task.copy()
            task_copy['timestamp'] = task['timestamp'].isoformat()
            serializable.append(task_copy)
            
        save_json({"history": serializable}, history_file)
        
    def send_notification(self, message):
        """텔레그램 알림 (안전한 전송)"""
        try:
            # 안전한 전송 메서드 사용
            success = self.notifier.send_message_safe(message)
            if not success:
                logger.warning("⚠️ 텔레그램 알림 전송 실패 (계속 진행)")
        except Exception as e:
            logger.warning(f"⚠️ 텔레그램 알림 오류 (무시됨): {e}")
            
    def stop_scheduler(self):
        """스케줄러 중지"""
        self.is_running = False
        if self.schedule_thread and self.schedule_thread.is_alive():
            self.schedule_thread.join(timeout=5)
            
        logger.info("🛑 스케줄러 중지됨")
        self.send_notification("🛑 자동 스케줄링 시스템 중지")
        
    def get_status(self):
        """현재 상태 조회"""
        recent_tasks = [t for t in self.task_history 
                       if t['timestamp'] > datetime.now() - timedelta(days=7)]
        
        success_rate = 0.0
        if recent_tasks:
            success_count = sum(1 for t in recent_tasks if t['success'])
            success_rate = (success_count / len(recent_tasks)) * 100
            
        return {
            'is_running': self.is_running,
            'last_dataset': self.last_dataset_creation.isoformat() if self.last_dataset_creation else None,
            'last_training': self.last_model_training.isoformat() if self.last_model_training else None,
            'total_tasks': len(self.task_history),
            'success_rate': success_rate
        }


class SchedulerController:
    """스케줄러 제어기"""
    
    def __init__(self):
        self.scheduler = None
        
    def start(self):
        """스케줄러 시작"""
        try:
            print("🚀 자동 스케줄링 시스템을 시작합니다...")
            
            self.scheduler = AutoSchedulingSystem()
            self.scheduler.start_scheduler()
            
            print("✅ 시스템이 시작되었습니다!")
            print("📅 스케줄:")
            print("  • 매일 09:00, 21:00: 데이터셋 + 모델 훈련")
            print("  • 매일 06:00: 시스템 상태 체크")
            print("  • 매주 일요일 03:00: 시스템 최적화")
            print("\\n⚠️ 중지하려면 Ctrl+C를 누르세요\\n")
            
            # 신호 처리
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            
            # 대기
            while True:
                time.sleep(60)
                
        except KeyboardInterrupt:
            self.stop()
        except Exception as e:
            print(f"❌ 시작 오류: {e}")
            self.stop()
            
    def stop(self):
        """스케줄러 중지"""
        if self.scheduler:
            print("\\n🛑 시스템을 중지합니다...")
            self.scheduler.stop_scheduler()
            print("✅ 중지되었습니다")
        sys.exit(0)
        
    def signal_handler(self, signum, frame):
        """신호 처리기"""
        self.stop()
        
    def status(self):
        """상태 조회"""
        try:
            scheduler = AutoSchedulingSystem()
            status = scheduler.get_status()
            
            print("\\n📊 스케줄러 상태:")
            print(f"  • 실행상태: {'🟢 실행중' if status['is_running'] else '🔴 중지'}")
            print(f"  • 마지막 데이터셋: {status['last_dataset'] or 'None'}")
            print(f"  • 마지막 훈련: {status['last_training'] or 'None'}")
            print(f"  • 총 작업: {status['total_tasks']}회")
            print(f"  • 성공률: {status['success_rate']:.1f}%")
            
        except Exception as e:
            print(f"❌ 상태 조회 실패: {e}")
            
    def test_dataset(self):
        """데이터셋 생성 테스트"""
        try:
            print("📊 데이터셋 생성 테스트...")
            scheduler = AutoSchedulingSystem()
            success = scheduler.create_dataset()
            print("✅ 성공!" if success else "❌ 실패!")
        except Exception as e:
            print(f"❌ 오류: {e}")
            
    def test_training(self):
        """모델 훈련 테스트"""
        try:
            print("🤖 ML 모델 훈련 테스트...")
            scheduler = AutoSchedulingSystem()
            success = scheduler.train_model()
            print("✅ 성공!" if success else "❌ 실패!")
        except Exception as e:
            print(f"❌ 오류: {e}")
            
    def test_full(self):
        """전체 업데이트 테스트"""
        try:
            print("🔄 전체 업데이트 테스트...")
            scheduler = AutoSchedulingSystem()
            scheduler.run_full_update()
        except Exception as e:
            print(f"❌ 오류: {e}")
            
    def health(self):
        """시스템 상태 체크"""
        try:
            print("🔍 시스템 상태 체크...")
            scheduler = AutoSchedulingSystem()
            scheduler.system_health_check()
            print("✅ 완료!")
        except Exception as e:
            print(f"❌ 오류: {e}")
            
    def help(self):
        """도움말"""
        print("\\n" + "="*60)
        print("🚀 통합 스케줄링 시스템 - CLI")
        print("="*60)
        print("\\n📋 기본 명령어:")
        print("  python scheduler.py start    - 스케줄러 시작")
        print("  python scheduler.py status   - 상태 조회")
        print("  python scheduler.py health   - 시스템 체크")
        print("\\n🧪 테스트 명령어:")
        print("  python scheduler.py test-dataset  - 데이터셋 테스트")
        print("  python scheduler.py test-training - 모델 훈련 테스트")
        print("  python scheduler.py test-full     - 전체 테스트")
        print("  python scheduler.py help          - 도움말")
        print("\\n📅 자동 스케줄:")
        print("  • 매일 09:00, 21:00: 데이터셋 + 모델 훈련")
        print("  • 매일 06:00: 시스템 상태 체크")
        print("  • 매주 일요일 03:00: 시스템 최적화")
        print("="*60)


def main():
    """메인 실행 함수"""
    if len(sys.argv) < 2:
        print("❌ 명령어를 지정해주세요")
        print("도움말: python scheduler.py help")
        return
        
    controller = SchedulerController()
    command = sys.argv[1].lower()
    
    if command == "start":
        controller.start()
    elif command == "status":
        controller.status()
    elif command == "health":
        controller.health()
    elif command == "test-dataset":
        controller.test_dataset()
    elif command == "test-training":
        controller.test_training()
    elif command == "test-full":
        controller.test_full()
    elif command == "help":
        controller.help()
    else:
        print(f"❌ 알 수 없는 명령어: {command}")
        print("도움말: python scheduler.py help")


if __name__ == "__main__":
    main()
