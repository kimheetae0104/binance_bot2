#!/usr/bin/env python3
"""
🚀 Streamlit Dashboard for Binance Trading Bot
바이낸스 하이브리드 AI 트레이딩 봇 대시보드
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime, timedelta
import time
from loguru import logger
from typing import List, Dict, Optional, Any

from utils import save_json, load_json, ensure_dir

# 페이지 설정
st.set_page_config(
    page_title="🚀 바이낸스 하이브리드 AI 트레이딩 봇",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일
st.markdown("""
<style>
    /* 전체 배경 */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* 메트릭 카드 스타일 */
    .metric-card {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        background: rgba(255, 255, 255, 0.15);
    }
    
    /* 색상 테마 */
    .positive { color: #10b981; }
    .negative { color: #ef4444; }
    .neutral { color: #f1f5f9; }
    
    /* 차트 컨테이너 */
    .chart-container {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    
    /* 사이드바 스타일 */
    .sidebar-card {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 12px;
        padding: 1rem;
        margin: 1rem 0;
        color: #333;
    }
</style>
""", unsafe_allow_html=True)


class TradingDashboard:
    """하이브리드 AI 트레이딩 봇 대시보드"""
    
    def __init__(self):
        self.data_dir = ensure_dir("dashboard_data")
        self.performance_file = self.data_dir / "performance.json"
        self.trades_file = self.data_dir / "trades.json"
        self.latest_snapshot_file = self.data_dir / "latest_snapshot.json"
        
        # 메모리에서 거래 데이터 관리
        self.trades = []
        self.load_existing_trades()
        logger.info("🎨 대시보드 초기화 완료")
    
    def load_existing_trades(self):
        """기존 거래 데이터 로드"""
        try:
            if self.trades_file.exists():
                trades_data = load_json(str(self.trades_file), {"trades": []})
                self.trades = trades_data.get("trades", [])
                logger.info(f"📊 기존 거래 데이터 로드: {len(self.trades)}건")
        except Exception as e:
            logger.error(f"거래 데이터 로드 실패: {e}")
            self.trades = []
    
    def update_trade_record(self, trade_record):
        """거래 기록 업데이트"""
        try:
            # 타임스탬프 추가
            if 'timestamp' not in trade_record:
                trade_record['timestamp'] = datetime.now().isoformat()
            
            # 거래 기록 추가
            self.trades.append(trade_record)
            
            # 파일에 저장
            trades_data = {"trades": self.trades}
            save_json(trades_data, str(self.trades_file))
            logger.info(f"📝 거래 기록 업데이트: {trade_record.get('symbol', 'Unknown')} {trade_record.get('side', '')}")
            
        except Exception as e:
            logger.error(f"거래 기록 업데이트 실패: {e}")
    
    def generate_dashboard_data(self, 
                              current_balance: float,
                              positions: Optional[List] = None,
                              trading_mode: str = "hybrid",
                              ml_confidence: float = 0.0,
                              last_signal: str = "none"):
        """대시보드 데이터 생성"""
        try:
            positions = positions or []
            
            # 기본 데이터 구조
            dashboard_data = {
                'timestamp': datetime.now().isoformat(),
                'current_status': {
                    'balance': current_balance,
                    'active_positions': len(positions),
                    'trading_mode': trading_mode,
                    'ml_confidence': ml_confidence,
                    'last_signal': last_signal,
                    'positions_detail': []
                },
                'performance': {
                    'trades': self.trades[-50:],  # 최근 50개 거래만
                    'total_trades': len(self.trades),
                    'win_rate': self.calculate_win_rate()
                }
            }
            
            # 포지션 세부 정보 추가
            for pos in positions:
                try:
                    if isinstance(pos, dict):
                        # 딕셔너리 형태의 포지션 데이터 처리
                        symbol = pos.get('symbol', '')
                        entry_price = pos.get('entry_price', 0) or pos.get('avg_price', 0)
                        current_price = pos.get('current_price', entry_price)
                        quantity = pos.get('quantity', 0)
                        
                        # PnL 계산
                        pnl_pct = 0
                        if entry_price > 0 and current_price > 0:
                            pnl_pct = ((current_price - entry_price) / entry_price) * 100
                        
                        pos_data = {
                            'symbol': symbol,
                            'entry_price': entry_price,
                            'current_price': current_price,
                            'quantity': quantity,
                            'value': quantity * current_price if current_price > 0 else 0,
                            'pnl_pct': pnl_pct
                        }
                        dashboard_data['current_status']['positions_detail'].append(pos_data)
                    elif hasattr(pos, 'symbol'):
                        # 객체 형태의 포지션 데이터 처리
                        entry_price = getattr(pos, 'entry_price', 0)
                        current_price = getattr(pos, 'current_price', entry_price)
                        quantity = getattr(pos, 'quantity', 0)
                        
                        # PnL 계산
                        pnl_pct = 0
                        if entry_price > 0 and current_price > 0:
                            pnl_pct = ((current_price - entry_price) / entry_price) * 100
                        
                        pos_data = {
                            'symbol': pos.symbol,
                            'entry_price': entry_price,
                            'current_price': current_price,
                            'quantity': quantity,
                            'value': quantity * current_price if current_price > 0 else 0,
                            'pnl_pct': pnl_pct
                        }
                        dashboard_data['current_status']['positions_detail'].append(pos_data)
                except Exception as e:
                    logger.warning(f"포지션 데이터 처리 실패: {e}")
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"대시보드 데이터 생성 실패: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'current_status': {
                    'balance': current_balance,
                    'active_positions': 0,
                    'trading_mode': trading_mode,
                    'positions_detail': []
                },
                'performance': {
                    'trades': [],
                    'total_trades': 0,
                    'win_rate': 0.0
                }
            }
    
    def save_dashboard_snapshot(self, dashboard_data):
        """대시보드 스냅샷 저장"""
        try:
            save_json(dashboard_data, str(self.latest_snapshot_file))
            logger.info("📸 대시보드 스냅샷 저장 완료")
        except Exception as e:
            logger.error(f"대시보드 스냅샷 저장 실패: {e}")
    
    def calculate_win_rate(self):
        """승률 계산"""
        try:
            if not self.trades:
                return 0.0
            
            # 수익이 나는 거래 계산
            profitable_trades = [t for t in self.trades if t.get('pnl_percent', 0) > 0 or t.get('profit', 0) > 0]
            
            if len(self.trades) == 0:
                return 0.0
            
            return len(profitable_trades) / len(self.trades) * 100
            
        except Exception as e:
            logger.error(f"승률 계산 실패: {e}")
            return 0.0
    
    def load_data(self):
        """대시보드 데이터 로드"""
        try:
            latest_file = self.data_dir / "latest_snapshot.json"
            if latest_file.exists():
                return load_json(str(latest_file), {})
            
            return {
                'timestamp': datetime.now().isoformat(),
                'current_status': {
                    'balance': 70.0,
                    'active_positions': 0,
                    'trading_mode': 'allin',
                    'positions_detail': []
                },
                'performance': {
                    'trades': [],
                    'total_trades': 0,
                    'win_rate': 0.0
                }
            }
        except Exception as e:
            logger.error(f"데이터 로드 실패: {e}")
            return {}
    
    def render_header(self):
        """헤더 렌더링"""
        current_time = datetime.now().strftime("%Y년 %m월 %d일 %H:%M:%S")
        
        st.markdown(f"""
        <div style="text-align: center; padding: 2rem; background: rgba(255,255,255,0.1); border-radius: 20px; margin-bottom: 2rem;">
            <h1 style="color: white; font-size: 2.5rem; margin-bottom: 0.5rem;">🚀 바이낸스 하이브리드 AI 트레이딩 봇</h1>
            <p style="color: rgba(255,255,255,0.8); font-size: 1.1rem;">
                실시간 페이퍼 트레이딩 성과 모니터링 | <strong>{current_time}</strong>
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    def render_metrics(self, data):
        """메트릭 카드 렌더링"""
        current_status = data.get('current_status', {})
        performance = data.get('performance', {})
        paper_trading = data.get('paper_trading', {})
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # 실제 현금 잔고 표시 (매수 후 남은 돈)
            usdt_balance = paper_trading.get('usdt_balance', 0)
            portfolio_value = paper_trading.get('total_value', current_status.get('balance', 0))
            
            st.metric(
                label="💰 현금 잔고",
                value=f"${usdt_balance:.2f}",
                delta=f"총 포트폴리오: ${portfolio_value:.2f}"
            )
        
        with col2:
            positions = current_status.get('active_positions', 0)
            st.metric(
                label="📊 활성 포지션",
                value=f"{positions}개",
                delta=None
            )
        
        with col3:
            total_trades = paper_trading.get('total_trades', len(performance.get('trades', [])))
            st.metric(
                label="📈 총 거래",
                value=f"{total_trades}회",
                delta=None
            )
        
        with col4:
            # 트레일링 익절 승률
            win_rate = paper_trading.get('win_rate', 0)
            return_pct = paper_trading.get('total_return_pct', 0)
            
            st.metric(
                label="🎯 승률",
                value=f"{win_rate:.1f}%",
                delta=f"수익률: {return_pct:+.2f}%"
            )
    
    def render_positions(self, data):
        """현재 포지션 렌더링"""
        st.markdown("### 💼 현재 보유 포지션")
        
        positions = data.get('current_status', {}).get('positions_detail', [])
        
        if not positions:
            st.info("현재 보유 중인 포지션이 없습니다.")
            
            # 트레일링 익절 설명 추가
            st.markdown("""
            #### 📈 **트레일링 익절 시스템**
            - **무제한 상승 추적**: 가격이 계속 오르면 계속 보유
            - **신고가 갱신 추적**: 최고가 달성할 때마다 트레일링 라인 상향 조정
            - **트레일링 익절**: 
              - 올인 모드: 신고가 대비 -1.5% 하락시 익절
              - 분할 모드: 신고가 대비 -0.8% 하락시 익절
            - **고정 손절**: -3% 도달시 무조건 손절
            
            **예시**: $1.00 → $1.50(+50%) → 트레일링 $1.488 → 익절!
            """)
        else:
            for pos in positions:
                symbol = pos.get('symbol', '')
                entry_price = pos.get('entry_price', 0)
                current_price = pos.get('current_price', entry_price)
                quantity = pos.get('quantity', 0)
                value = current_price * quantity
                pnl_pct = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
                
                # 현재 신고가 예상 (진입가와 현재가 중 높은 값)
                assumed_high = max(entry_price, current_price)
                
                # 올인/분할 모드 추정 (실제로는 포지션 정보에서 가져와야 함)
                is_allin = value > 50  # 임시 추정: 큰 포지션이면 올인으로 간주
                trailing_pct = 0.015 if is_allin else 0.008
                
                # 트레일링 라인과 손절선 계산  
                trailing_line = assumed_high * (1 - trailing_pct)
                stop_loss_price = entry_price * 0.97  # -3% 손절선
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.write(f"**{symbol}**")
                    st.caption(f"가치: ${value:.2f}")
                with col2:
                    st.write(f"수량: {quantity:.4f}")
                    mode_text = "올인" if is_allin else "분할"
                    st.caption(f"모드: {mode_text} ({trailing_pct:.1%})")
                with col3:
                    st.write(f"진입가: ${entry_price:.6f}")
                    st.write(f"현재가: ${current_price:.6f}")
                with col4:
                    color = "🟢" if pnl_pct >= 0 else "🔴"
                    st.write(f"{color} {pnl_pct:+.2f}%")
                    if current_price > entry_price * 1.02:  # 2% 이상 수익시
                        st.caption(f"🚀 트레일링: ${trailing_line:.6f}")
                    else:
                        st.caption(f"📊 손절선: ${stop_loss_price:.6f}")
    
    def render_recent_trades(self, data):
        """최근 거래 렌더링"""
        st.markdown("### 📋 최근 거래 내역")
        
        trades = data.get('performance', {}).get('trades', [])
        
        if not trades:
            st.info("아직 거래 내역이 없습니다.")
        else:
            recent_trades = trades[-10:]  # 최근 10개
            
            trade_data = []
            for trade in recent_trades:
                # 거래 타입 확인
                side = trade.get('side', '').lower()
                trade_type = trade.get('type', '')
                
                # 매수/매도 구분
                if side == 'buy' and trade_type == 'entry':
                    action = "🟢 매수"
                    status = "완료"
                elif side == 'sell' and trade_type == 'exit':
                    action = "🔴 매도"
                    status = "완료"
                else:
                    action = f"{side.upper()}"
                    status = "완료"
                
                # 수익률 계산
                profit_pct = trade.get('profit_pct', 0) or trade.get('pnl_percent', 0)
                profit_display = f"{profit_pct:+.2f}%" if profit_pct != 0 else "-"
                
                trade_data.append({
                    '심볼': trade.get('symbol', ''),
                    '액션': action,
                    '가격': f"${trade.get('price', 0):.6f}",
                    '수량': f"{trade.get('quantity', 0):.4f}",
                    '금액': f"${trade.get('value', 0):.2f}",
                    '수익률': profit_display,
                    '상태': status,
                    '시간': pd.to_datetime(trade.get('timestamp', '')).strftime('%m-%d %H:%M') if trade.get('timestamp') else '-'
                })
            
            if trade_data:
                df = pd.DataFrame(trade_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
    
    def render_performance_chart(self, data):
        """성과 차트 렌더링"""
        st.markdown("### 📊 누적 수익률 차트")
        
        trades = data.get('performance', {}).get('trades', [])
        
        if not trades:
            st.info("차트를 표시할 거래 데이터가 없습니다.")
            return
        
        # 누적 수익률 계산
        cumulative_returns = []
        cumulative_pnl = 0
        
        for i, trade in enumerate(trades):
            pnl = trade.get('pnl_percent', 0)
            cumulative_pnl += pnl
            cumulative_returns.append({
                'trade_num': i + 1,
                'cumulative_return': cumulative_pnl
            })
        
        df = pd.DataFrame(cumulative_returns)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['trade_num'],
            y=df['cumulative_return'],
            mode='lines+markers',
            name='누적 수익률 (%)',
            line=dict(color='#10b981', width=3),
            marker=dict(size=6)
        ))
        
        fig.update_layout(
            title="누적 수익률 변화",
            xaxis_title="거래 번호",
            yaxis_title="누적 수익률 (%)",
            height=400,
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_sidebar(self, data):
        """사이드바 렌더링"""
        with st.sidebar:
            st.markdown("""
            <div class="sidebar-card">
                <h2>⚙️ 대시보드 설정</h2>
            </div>
            """, unsafe_allow_html=True)
            
            # 자동 새로고침
            auto_refresh = st.checkbox("🔄 자동 새로고침 (30초)", value=False)
            if auto_refresh:
                time.sleep(30)
                st.rerun()
            
            st.divider()
            
            # 시스템 상태 체크
            st.markdown("""
            <div class="sidebar-card">
                <h3>🤖 시스템 상태</h3>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🔍 시스템 상태 체크"):
                try:
                    from utils import check_system_health, validate_trading_config
                    
                    # 시스템 헬스 체크
                    health = check_system_health()
                    
                    for check_name, check_result in health['checks'].items():
                        status_icon = "✅" if check_result['status'] == 'ok' else "⚠️" if check_result['status'] == 'warning' else "❌"
                        st.write(f"{status_icon} {check_name.title()}")
                    
                    # 설정 유효성 체크
                    config_valid = validate_trading_config()
                    if config_valid['overall']:
                        st.success("🎯 트레이딩 설정 정상")
                    else:
                        st.warning("⚠️ 설정 확인 필요")
                        
                except Exception as e:
                    st.error(f"상태 체크 실패: {e}")
            
            # 상위 코인 정보
            st.markdown("""
            <div class="sidebar-card">
                <h3>📈 상위 코인</h3>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🔝 상위 코인 조회"):
                try:
                    from utils import get_current_top_coins
                    top_coins = get_current_top_coins()
                    
                    if top_coins:
                        for coin in top_coins[:5]:  # 상위 5개만 표시
                            st.write(f"**{coin['symbol']}**: ${coin['price']:.6f}")
                    else:
                        st.warning("데이터를 가져올 수 없습니다")
                except Exception as e:
                    st.error(f"코인 정보 조회 실패: {e}")
            
            st.divider()
            
            # 기존 시스템 정보
            st.markdown("""
            <div class="sidebar-card">
                <h3>🤖 시스템 정보</h3>
                <p><strong>모드:</strong> 하이브리드 AI</p>
                <p><strong>ML 임계값:</strong> 25%</p>
                <p><strong>상태:</strong> 🟢 실행중</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.divider()
            
            # 컨트롤
            if st.button("🔄 수동 새로고침", use_container_width=True):
                st.rerun()
    
    def run(self):
        """대시보드 실행"""
        # 헤더
        self.render_header()
        
        # 데이터 로드
        with st.spinner('📊 최신 데이터 로딩 중...'):
            data = self.load_data()
        
        # 메트릭
        self.render_metrics(data)
        
        st.divider()
        
        # 포지션과 차트
        col1, col2 = st.columns([1, 1])
        
        with col1:
            self.render_positions(data)
        
        with col2:
            self.render_performance_chart(data)
        
        st.divider()
        
        # 거래 내역
        self.render_recent_trades(data)
        
        # 사이드바
        self.render_sidebar(data)
        
        # 마지막 업데이트 시간
        if data.get('timestamp'):
            update_time = pd.to_datetime(data['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            st.caption(f"마지막 업데이트: {update_time}")


def main():
    """메인 함수"""
    try:
        dashboard = TradingDashboard()
        dashboard.run()
    except Exception as e:
        st.error(f"대시보드 실행 오류: {e}")
        logger.error(f"대시보드 오류: {e}")


if __name__ == "__main__":
    main()
