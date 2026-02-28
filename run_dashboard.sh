#!/bin/bash

# 🚀 Trading Dashboard Launcher
# 바이낸스 ML 트레이딩 봇 - 현대적 대시보드 실행기

echo "🎨 Trading Dashboard 시작 중..."
echo "=============================================="

# Python 환경 확인
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3가 설치되어 있지 않습니다."
    exit 1
fi

# Streamlit 설치 확인
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "📦 Streamlit 설치 중..."
    pip3 install streamlit plotly loguru
fi

# 포트 확인 및 설정
PORT=8501
while netstat -aln | grep -q ":$PORT.*LISTEN"; do
    echo "⚠️ 포트 $PORT가 이미 사용 중입니다. 다른 포트를 시도합니다."
    PORT=$((PORT + 1))
done

echo "🌐 대시보드를 포트 $PORT에서 실행합니다."
echo ""
echo "📋 대시보드 기능:"
echo "  • 실시간 트레이딩 성과 모니터링"
echo "  • ML 모델 성능 분석"
echo "  • 인터랙티브 차트 및 그래프"
echo "  • 거래 기록 및 통계"
echo "  • 현대적이고 반응형 UI"
echo ""
echo "🔗 브라우저에서 다음 주소로 접속하세요:"
echo "   http://localhost:$PORT"
echo ""
echo "⌨️ 종료하려면 Ctrl+C를 누르세요."
echo "=============================================="

# Streamlit 실행
streamlit run dashboard.py \
    --server.port $PORT \
    --server.headless true \
    --browser.gatherUsageStats false \
    --theme.base dark \
    --theme.primaryColor "#667eea" \
    --theme.backgroundColor "#0c0c0c" \
    --theme.secondaryBackgroundColor "#1a1a1a" \
    --theme.textColor "#ffffff"
