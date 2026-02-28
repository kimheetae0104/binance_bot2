#!/bin/bash

# 바이낸스 ML 트레이딩 봇 시스템 통합 실행 스크립트

echo "🚀 바이낸스 ML 트레이딩 봇 시스템"
echo "================================="

# Python 실행 환경 체크
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3가 설치되어 있지 않습니다."
    exit 1
fi

# 필요한 패키지 체크
echo "📦 시스템 의존성 체크 중..."
python3 -c "
try:
    import pandas, numpy, sklearn, loguru, ccxt, telegram, streamlit
    print('✅ 모든 필수 패키지가 설치되어 있습니다.')
except ImportError as e:
    print(f'❌ 누락된 패키지: {e}')
    print('📦 다음 명령으로 설치하세요: pip install -r requirements.txt')
    exit(1)
"

if [ $? -ne 0 ]; then
    exit 1
fi

while true; do
    echo ""
    echo "🎛️ 시스템 제어 메뉴"
    echo "1. 🚀 전체 시스템 시작 (트레이딩 + 스케줄러)"
    echo "2. 🤖 페이퍼 트레이딩 봇 시작"
    echo "3. 📊 대시보드 실행"
    echo "4. 🔍 시스템 상태 체크"
    echo "5. 📈 모델 훈련 실행"
    echo "6. 📖 도움말"
    echo "0. 👋 종료"
    echo ""
    read -p "선택하세요 (0-6): " choice

    case $choice in
        1)
            echo "🚀 전체 시스템을 시작합니다..."
            echo "⚠️ 이 모드는 실제 트레이딩과 자동 스케줄링을 포함합니다."
            read -p "계속하시겠습니까? (y/N): " confirm
            if [[ $confirm == [yY] ]]; then
                python3 system_launcher.py
            fi
            ;;
        2)
            echo "🤖 페이퍼 트레이딩 봇을 시작합니다..."
            echo "💰 가상 자금으로 안전한 트레이딩을 시작합니다."
            python3 paper_main.py
            ;;
        3)
            echo "📊 대시보드를 실행합니다..."
            echo "🌐 브라우저에서 http://localhost:8501 로 접속하세요."
            ./run_dashboard.sh
            ;;
        4)
            echo "🔍 시스템 상태를 확인합니다..."
            python3 -c "
import sys
sys.path.append('.')
from system_launcher import SystemLauncher
launcher = SystemLauncher()
launcher.check_system_readiness()
"
            ;;
        5)
            echo "📈 ML 모델 훈련을 시작합니다..."
            python3 train_production_model.py
            ;;
        6)
            echo "📖 도움말"
            echo "================================="
            echo "🚀 전체 시스템: 실제 트레이딩 + 자동화"
            echo "🤖 페이퍼 트레이딩: 가상 자금으로 안전한 트레이딩"
            echo "📊 대시보드: 실시간 성과 모니터링"
            echo "🔍 상태 체크: 시스템 준비도 확인"
            echo "📈 모델 훈련: ML 모델 업데이트"
            echo ""
            echo "📋 주요 파일:"
            echo "  • config.py: 트레이딩 설정"
            echo "  • .env: API 키 및 비밀 정보"
            echo "  • dashboard.py: 실시간 대시보드"
            echo "  • paper_main.py: 페이퍼 트레이딩"
            echo ""
            echo "📚 자세한 내용은 README.md를 참고하세요."
            ;;
        0)
            echo "👋 시스템을 종료합니다."
            break
            ;;
        *)
            echo "❌ 잘못된 선택입니다. 0-6 사이의 숫자를 입력하세요."
            ;;
    esac
    
    echo ""
    echo "🔄 메뉴로 돌아가려면 Enter를 누르세요..."
    read
done
            python system_launcher.py trading
            ;;
        3)
            echo "📅 자동 스케줄러만 시작합니다..."
            python system_launcher.py scheduler
            ;;
        4)
            echo "📊 시스템 대시보드를 열니다..."
            python system_dashboard.py
            ;;
        5)
            echo "🔍 시스템 상태를 조회합니다..."
            python system_launcher.py status
            ;;
        6)
            echo "🧪 테스트 메뉴를 엽니다..."
            echo ""
            echo "테스트 메뉴:"
            echo "a. 📊 데이터셋 생성 테스트"
            echo "b. 🤖 모델 훈련 테스트" 
            echo "c. 🔄 전체 업데이트 테스트"
            echo "d. 🔍 시스템 상태 체크"
            echo ""
            read -p "테스트를 선택하세요 (a-d): " test_choice
            
            case $test_choice in
                a)
                    python scheduler_control.py test-dataset
                    ;;
                b)
                    python scheduler_control.py test-training
                    ;;
                c)
                    python scheduler_control.py test-full
                    ;;
                d)
                    python scheduler_control.py health
                    ;;
                *)
                    echo "❌ 잘못된 선택입니다."
                    ;;
            esac
            ;;
        7)
            echo ""
            echo "📖 바이낸스 ML 트레이딩 봇 시스템 도움말"
            echo "======================================="
            echo ""
            echo "🎯 시스템 구성:"
            echo "  • 🤖 ML 트레이딩 봇: 실시간 급등 패턴 감지 및 자동 매매"
            echo "  • 📅 자동 스케줄러: 매일 정해진 시간에 데이터셋 생성 + 모델 훈련"
            echo "  • 📊 시스템 대시보드: 실시간 시스템 상태 모니터링"
            echo ""
            echo "📅 자동 실행 스케줄:"
            echo "  • 매일 09:00, 21:00: 데이터셋 생성 + 모델 훈련"
            echo "  • 매일 06:00: 시스템 상태 체크"
            echo "  • 매주 일요일 03:00: 전체 시스템 최적화"
            echo ""
            echo "🔧 수동 실행 명령어:"
            echo "  python system_launcher.py full      - 전체 시스템 시작"
            echo "  python system_launcher.py trading   - 트레이딩 봇만 시작"
            echo "  python system_launcher.py scheduler - 스케줄러만 시작"
            echo "  python system_launcher.py status    - 시스템 상태 조회"
            echo "  python system_dashboard.py          - 대화형 대시보드"
            echo "  python system_dashboard.py monitor  - 실시간 모니터링"
            echo "  python scheduler_control.py test-full - 테스트 실행"
            echo ""
            echo "⚠️ 주의사항:"
            echo "  • .env 파일에 바이낸스 API 키와 텔레그램 설정이 필요합니다"
            echo "  • 처음 실행 시 데이터셋 생성에 시간이 걸릴 수 있습니다"
            echo "  • 페이퍼 트레이딩 모드로 안전하게 테스트할 수 있습니다"
            echo ""
            ;;
        0)
            echo "👋 시스템을 종료합니다."
            break
            ;;
        *)
            echo "❌ 잘못된 선택입니다. 다시 선택해주세요."
            ;;
    esac
    
    echo ""
    read -p "⏸️ 계속하려면 Enter를 누르세요..."
done
