#!/usr/bin/env python3
"""
바이낸스 ML 트레이딩 봇 통합 런처
- 메인 트레이딩 봇과 자동 스케줄러를 함께 실행
"""

import sys
import os
import signal
import time
import threading
from datetime import datetime
from pathlib import Path
from loguru import logger

# 모듈 임포트
from main import TradingBot
from scheduler import AutoSchedulingSystem
from config import load_config

class SystemLauncher:
    """시스템 통합 런처"""
    
    def __init__(self):
        self.config = load_config()
        self.trading_bot = None
        self.scheduler = None
        self.is_running = False
    
    def check_system_readiness(self):
        """시스템 준비 상태 종합 검증"""
        print("🎯 바이낸스 ML 트레이딩 봇 시스템 검증")
        print("=" * 60)
        
        checks = {
            "데이터셋": False,
            "모델 파일": False,
            "설정 파일": False,
            "핵심 모듈": False
        }
        
        # 1. 데이터셋 검증
        print("\n📊 1. 데이터셋 검증")
        try:
            data_files = []
            data_dir = Path('data')
            advanced_dir = Path('advanced_datasets')
            
            if data_dir.exists():
                data_files.extend([f for f in data_dir.glob('*.csv')])
            if advanced_dir.exists():
                data_files.extend([f for f in advanced_dir.glob('*.csv')])
                
            if data_files:
                latest = max(data_files, key=lambda x: x.stat().st_mtime)
                file_size = latest.stat().st_size / 1024 / 1024
                
                with open(latest, 'r') as f:
                    header = f.readline().strip()
                feature_count = len(header.split(','))
                
                print(f"   ✅ 최신 데이터: {latest.name}")
                print(f"   ✅ 파일 크기: {file_size:.1f} MB")
                print(f"   ✅ 특성 수: {feature_count}개")
                
                if file_size > 5 and feature_count > 30:
                    print(f"   ✅ 고품질 ML 데이터셋 준비됨")
                    checks["데이터셋"] = True
                else:
                    print(f"   ⚠️ 데이터셋 품질 재확인 필요")
            else:
                print("   ❌ 훈련 데이터 파일 없음")
        except Exception as e:
            print(f"   ❌ 데이터셋 검증 실패: {e}")
        
        # 2. 모델 파일 검증
        print("\n🧠 2. ML 모델 파일 검증")
        try:
            models_dir = Path('models')
            if models_dir.exists():
                model_files = list(models_dir.glob('*.pkl'))
                if model_files:
                    print(f"   ✅ 발견된 모델: {len(model_files)}개")
                    for model in model_files:
                        size_mb = model.stat().st_size / 1024 / 1024
                        print(f"     • {model.name} ({size_mb:.2f} MB)")
                    checks["모델 파일"] = True
                else:
                    print("   ❌ 모델 파일 없음")
            else:
                print("   ❌ models 디렉토리 없음")
        except Exception as e:
            print(f"   ❌ 모델 검증 실패: {e}")
        
        # 3. 설정 파일 검증
        print("\n⚙️ 3. 설정 파일 검증")
        try:
            if Path('.env').exists():
                print("   ✅ .env 파일 존재")
                # API 키 확인
                if self.config.BINANCE_API_KEY and self.config.BINANCE_SECRET_KEY:
                    print("   ✅ Binance API 키 설정됨")
                else:
                    print("   ⚠️ Binance API 키 미설정")
                    
                if self.config.TELEGRAM_BOT_TOKEN and self.config.TELEGRAM_CHAT_ID:
                    print("   ✅ Telegram 설정됨")
                else:
                    print("   ⚠️ Telegram 설정 미완료")
                checks["설정 파일"] = True
            else:
                print("   ❌ .env 파일 없음")
        except Exception as e:
            print(f"   ❌ 설정 검증 실패: {e}")
        
        # 4. 핵심 모듈 검증
        print("\n🔧 4. 핵심 모듈 검증")
        try:
            required_files = [
                'binance_api.py', 'advanced_ml_predictor.py', 'smart_strategy.py',
                'paper_trading.py', 'telegram_notifier.py', 'dashboard.py'
            ]
            
            missing_files = []
            for file in required_files:
                if not Path(file).exists():
                    missing_files.append(file)
                else:
                    print(f"   ✅ {file}")
            
            if not missing_files:
                checks["핵심 모듈"] = True
                print("   ✅ 모든 핵심 모듈 존재")
            else:
                print(f"   ❌ 누락된 파일: {missing_files}")
        except Exception as e:
            print(f"   ❌ 모듈 검증 실패: {e}")
        
        # 결과 요약
        print("\n" + "=" * 60)
        print("📋 시스템 준비 상태 요약")
        print("=" * 60)
        
        ready_count = sum(checks.values())
        total_count = len(checks)
        
        for category, status in checks.items():
            status_icon = "✅" if status else "❌"
            print(f"   {status_icon} {category}")
        
        print(f"\n🎯 전체 준비도: {ready_count}/{total_count} ({ready_count/total_count*100:.1f}%)")
        
        if ready_count == total_count:
            print("🎉 시스템이 완전히 준비되었습니다! 🚀")
            return True
        elif ready_count >= total_count * 0.7:
            print("⚠️ 시스템이 부분적으로 준비되었습니다. 일부 기능 제한 가능")
            return True
        else:
            print("❌ 시스템 준비가 불완전합니다. 설정을 완료해주세요.")
            return False
        
    def start_full_system(self):
        """전체 시스템 시작"""
        try:
            self.is_running = True
            
            print("🚀 바이낸스 ML 트레이딩 봇 시스템을 시작합니다...")
            print("=" * 60)
            
            # 시스템 준비 상태 체크
            if not self.check_system_readiness():
                print("\n❌ 시스템이 준비되지 않았습니다. 설정을 완료한 후 다시 시도하세요.")
                return False
            
            print("\n" + "=" * 60)
            print("🎯 시스템 시작 중...")
            print("=" * 60)
            
            # 1. 자동 스케줄러 시작
            print("📅 자동 스케줄링 시스템 시작...")
            self.scheduler = AutoSchedulingSystem()
            self.scheduler.start_scheduler()
            print("✅ 스케줄링 시스템 시작 완료!")
            
            # 2. 메인 트레이딩 봇 시작 (별도 스레드)
            print("🤖 메인 트레이딩 봇 시작...")
            self.start_trading_bot_thread()
            
            print("\n" + "=" * 60)
            print("🎉 전체 시스템이 성공적으로 시작되었습니다!")
            print("\n📊 실행 중인 컴포넌트:")
            print("  • 🤖 ML 트레이딩 봇 (실시간 트레이딩)")
            print("  • 📅 자동 스케줄러 (데이터셋 생성 + 모델 훈련)")
            print("  • 🔍 시스템 모니터링")
            print("\n📅 자동 실행 스케줄:")
            print("  • 매일 09:00, 21:00: 데이터셋 생성 + 모델 훈련")
            print("  • 매일 06:00: 시스템 상태 체크")
            print("  • 매주 일요일 03:00: 전체 시스템 최적화")
            print("\n⚠️ 시스템을 중지하려면 Ctrl+C를 누르세요.")
            print("=" * 60)
            
            # 신호 핸들러 설정
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            
            # 무한 대기
            while self.is_running:
                time.sleep(10)
                
            return True
                
        except KeyboardInterrupt:
            self.shutdown_system()
        except Exception as e:
            logger.error(f"시스템 시작 오류: {str(e)}")
            self.shutdown_system()
            return False
            
    def start_trading_bot_thread(self):
        """트레이딩 봇 스레드 시작"""
        def run_trading_bot():
            try:
                self.trading_bot = TradingBot()
                # 비동기 실행
                import asyncio
                asyncio.run(self.trading_bot.run_async())
            except Exception as e:
                logger.error(f"트레이딩 봇 오류: {str(e)}")
                
        bot_thread = threading.Thread(target=run_trading_bot, daemon=True)
        bot_thread.start()
        
        # 잠시 대기하여 봇 시작 확인
        time.sleep(3)
        print("✅ 트레이딩 봇 시작 완료!")
        
    def signal_handler(self, signum, frame):
        """신호 핸들러"""
        print("\n\n🛑 시스템 종료 신호를 받았습니다...")
        self.shutdown_system()
        
    def shutdown_system(self):
        """시스템 종료"""
        if not self.is_running:
            return
            
        self.is_running = False
        print("🛑 시스템을 안전하게 종료합니다...")
        
        # 스케줄러 중지
        if self.scheduler:
            print("📅 스케줄러를 중지합니다...")
            self.scheduler.stop_scheduler()
            
        # 트레이딩 봇 중지
        if self.trading_bot:
            print("🤖 트레이딩 봇을 중지합니다...")
            try:
                self.trading_bot.stop()
            except:
                pass
                
        print("✅ 시스템이 안전하게 종료되었습니다.")
        sys.exit(0)
        
    def start_trading_only(self):
        """트레이딩 봇만 시작"""
        try:
            print("🤖 트레이딩 봇만 시작합니다...")
            
            self.trading_bot = TradingBot()
            
            # 신호 핸들러 설정
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            
            # 비동기 실행
            import asyncio
            asyncio.run(self.trading_bot.run_async())
                
        except KeyboardInterrupt:
            print("\n🛑 트레이딩 봇을 중지합니다...")
        except Exception as e:
            logger.error(f"트레이딩 봇 오류: {str(e)}")
            
    def start_scheduler_only(self):
        """스케줄러만 시작"""
        try:
            print("📅 자동 스케줄러만 시작합니다...")
            
            self.scheduler = AutoSchedulingSystem()
            self.scheduler.start_scheduler()
            
            # 신호 핸들러 설정
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            
            # 무한 대기
            while True:
                time.sleep(60)
                
        except KeyboardInterrupt:
            print("\n🛑 스케줄러를 중지합니다...")
            if self.scheduler:
                self.scheduler.stop_scheduler()
                
    def show_status(self):
        """시스템 상태 표시"""
        print("\n📊 바이낸스 ML 트레이딩 봇 시스템 상태")
        print("=" * 50)
        
        try:
            # 스케줄러 상태
            scheduler = AutoSchedulingSystem()
            scheduler_status = scheduler.get_status()
            
            print("📅 자동 스케줄러:")
            print(f"  • 상태: {'🟢 실행중' if scheduler_status['is_running'] else '🔴 중지됨'}")
            print(f"  • 마지막 데이터셋: {scheduler_status['last_dataset_creation'] or 'None'}")
            print(f"  • 마지막 훈련: {scheduler_status['last_model_training'] or 'None'}")
            print(f"  • 성공률: {scheduler_status['recent_success_rate']:.1f}%")
            
        except Exception as e:
            print(f"📅 스케줄러 상태: ❌ 조회 실패 ({str(e)})")
            
        # 파일 상태 체크
        self.check_file_status()
        
    def check_file_status(self):
        """파일 상태 체크"""
        print("\n📁 파일 상태:")
        
        # 모델 파일
        model_path = "models/xgboost_model_new.pkl"
        if os.path.exists(model_path):
            model_time = datetime.fromtimestamp(os.path.getmtime(model_path))
            print(f"  • 🤖 ML 모델: ✅ 정상 ({model_time.strftime('%m/%d %H:%M')})")
        else:
            print("  • 🤖 ML 모델: ❌ 파일 없음")
            
        # 데이터셋 파일
        dataset_dir = "advanced_datasets"
        if os.path.exists(dataset_dir):
            files = [f for f in os.listdir(dataset_dir) if f.endswith('.csv')]
            if files:
                latest_file = max(files, key=lambda x: os.path.getmtime(os.path.join(dataset_dir, x)))
                file_time = datetime.fromtimestamp(os.path.getmtime(os.path.join(dataset_dir, latest_file)))
                print(f"  • 📊 데이터셋: ✅ 정상 ({len(files)}개, 최신: {file_time.strftime('%m/%d %H:%M')})")
            else:
                print("  • 📊 데이터셋: ⚠️ 파일 없음")
        else:
            print("  • 📊 데이터셋: ❌ 디렉토리 없음")
            
        # 설정 파일
        if os.path.exists(".env"):
            print("  • ⚙️ 설정: ✅ 정상")
        else:
            print("  • ⚙️ 설정: ❌ .env 파일 없음")
            
    def show_help(self):
        """도움말 표시"""
        print("\n📖 바이낸스 ML 트레이딩 봇 시스템 런처")
        print("=" * 50)
        print("python system_launcher.py [명령어]")
        print("\n🚀 실행 명령어:")
        print("  full      - 전체 시스템 시작 (트레이딩 + 스케줄러)")
        print("  trading   - 트레이딩 봇만 시작")
        print("  scheduler - 자동 스케줄러만 시작")
        print("  status    - 시스템 상태 조회")
        print("  help      - 도움말 표시")
        print("\n📊 시스템 구성:")
        print("  • 🤖 ML 트레이딩 봇: 실시간 급등 패턴 감지 및 자동 매매")
        print("  • 📅 자동 스케줄러: 데이터셋 생성 및 모델 재훈련")
        print("  • 🔍 시스템 모니터링: 상태 체크 및 최적화")
        print("\n📅 자동 스케줄:")
        print("  • 매일 09:00, 21:00: 데이터셋 생성 + 모델 훈련")
        print("  • 매일 06:00: 시스템 상태 체크")
        print("  • 매주 일요일 03:00: 전체 시스템 최적화")


def main():
    """메인 실행 함수"""
    launcher = SystemLauncher()
    
    if len(sys.argv) < 2:
        print("❌ 명령어를 지정해주세요.")
        launcher.show_help()
        return
        
    command = sys.argv[1].lower()
    
    if command == "full":
        launcher.start_full_system()
    elif command == "trading":
        launcher.start_trading_only()
    elif command == "scheduler":
        launcher.start_scheduler_only()
    elif command == "status":
        launcher.show_status()
    elif command == "help":
        launcher.show_help()
    else:
        print(f"❌ 알 수 없는 명령어: {command}")
        launcher.show_help()


if __name__ == "__main__":
    main()
