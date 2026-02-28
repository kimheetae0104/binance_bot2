"""
단타 매매 전용 전략
- 빠른 진입/청산
- 타이트한 손익 관리
- 시간 기반 강제 청산
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
from loguru import logger

from smart_strategy import SmartTradingStrategy
from trading_strategy import Position, TradeSignal

class ScalpingStrategy(SmartTradingStrategy):
    """단타 매매 전문 전략"""
    
    def __init__(self, config):
        super().__init__(config)
        self.config = config
        
        # 단타 전용 설정
        self.max_hold_minutes = getattr(config, 'MAX_HOLD_MINUTES', 180)  # 3시간
        self.quick_exit_threshold = getattr(config, 'QUICK_EXIT_THRESHOLD', 0.015)  # 1.5%
        self.scalping_mode = getattr(config, 'SCALPING_MODE', True)
        
        # 단타 통계
        self.scalp_stats = {
            'quick_exits': 0,
            'time_exits': 0,
            'avg_hold_minutes': 0,
            'best_scalp': 0.0,
            'total_scalps': 0
        }
        
        logger.info(f"🎯 단타 전략 초기화: 최대보유 {self.max_hold_minutes}분")
    
    def create_scalping_stops(self, entry_price: float, trading_mode: str) -> Tuple[float, float, float]:
        """단타용 손익 설정"""
        # 더 타이트한 손절
        stop_loss = entry_price * (1 - self.config.STOP_LOSS_PCT)
        
        # 빠른 익절
        quick_target = entry_price * (1 + self.quick_exit_threshold)
        take_profit = entry_price * (1 + self.config.TAKE_PROFIT_PCT)
        
        logger.info(f"🎯 단타 설정: 손절 ${stop_loss:.6f}, "
                   f"빠른익절 ${quick_target:.6f}, 목표 ${take_profit:.6f}")
        
        return stop_loss, quick_target, take_profit
    
    def should_quick_exit(self, position: Position, current_price: float) -> Tuple[bool, str]:
        """빠른 익절 조건 확인"""
        pnl_pct = ((current_price - position.entry_price) / position.entry_price)
        
        # 빠른 익절 조건 (1.5% 이상)
        if pnl_pct >= self.quick_exit_threshold:
            return True, "quick_profit"
        
        # 시간 기반 강제 청산
        hold_minutes = (datetime.now() - position.entry_time).total_seconds() / 60
        
        if hold_minutes >= self.max_hold_minutes:
            if pnl_pct > 0:
                return True, "time_profit"
            else:
                return True, "time_cut"
        
        # 부분 익절 (2% 도달시 절반 매도 고려)
        if pnl_pct >= 0.02 and not hasattr(position, 'partial_exit_done'):
            return True, "partial_profit"
        
        return False, ""
    
    def manage_scalping_position(self, symbol: str, position: Position, 
                                current_price: float) -> Tuple[bool, str]:
        """단타 포지션 관리"""
        # 기본 손익 확인
        should_exit, exit_reason = super().manage_position_smart(symbol, position, current_price)
        
        if should_exit:
            return True, exit_reason
        
        # 단타 전용 확인
        quick_exit, quick_reason = self.should_quick_exit(position, current_price)
        
        if quick_exit:
            # 단타 통계 업데이트
            hold_minutes = (datetime.now() - position.entry_time).total_seconds() / 60
            
            if quick_reason == "quick_profit":
                self.scalp_stats['quick_exits'] += 1
            elif "time" in quick_reason:
                self.scalp_stats['time_exits'] += 1
            
            # 평균 보유 시간 업데이트
            total_holds = self.scalp_stats['total_scalps']
            avg_hold = self.scalp_stats['avg_hold_minutes']
            new_avg = (avg_hold * total_holds + hold_minutes) / (total_holds + 1)
            self.scalp_stats['avg_hold_minutes'] = new_avg
            self.scalp_stats['total_scalps'] += 1
            
            logger.info(f"⚡ 단타 청산: {symbol} ({hold_minutes:.1f}분 보유, {quick_reason})")
            
            return True, quick_reason
        
        return False, ""
    
    def execute_scalping_trade(self, best_prediction: Dict, current_balance: float, 
                             current_positions: Dict) -> Optional[Position]:
        """단타 매매 실행"""
        if not self.should_make_trade(current_balance, current_positions):
            return None
        
        # 높은 확률만 단타 매매
        if best_prediction.get('ensemble_probability', 0) < self.config.ML_PROB_THRESHOLD:
            logger.info(f"💤 확률 부족: {best_prediction.get('ensemble_probability', 0):.2%} < {self.config.ML_PROB_THRESHOLD:.2%}")
            return None
        
        # 신호 분석
        signal = self.analyze_signal(best_prediction, current_positions)
        
        if signal.action != 'buy':
            return None
        
        # 매매 모드 결정
        trading_mode = self.get_trading_mode(current_balance)
        
        # 단타용 포지션 크기 (더 작게)
        if trading_mode == 'allin':
            # 올인 모드라도 단타는 80%만 투자 (안전)
            position_size = current_balance * 0.80
        else:
            # 분할 모드는 15%로 더 보수적
            position_size = current_balance * 0.15
        
        if position_size < 10:
            return None
        
        # 단타용 손익 설정
        stop_loss, quick_target, take_profit = self.create_scalping_stops(
            signal.current_price, trading_mode
        )
        
        # 포지션 생성
        position = Position(
            symbol=signal.symbol,
            entry_price=signal.current_price,
            quantity=position_size / signal.current_price,
            entry_time=signal.timestamp,
            stop_loss=stop_loss,
            take_profit=take_profit,
            highest_price=signal.current_price,
            entry_reason=f"scalp_{trading_mode}_{signal.confidence}"
        )
        
        # 빠른 익절 가격도 저장
        position.quick_target = quick_target
        
        # 포지션 저장
        self.positions[signal.symbol] = position
        self.save_positions()
        
        # 통계 업데이트
        if trading_mode == 'allin':
            self.allin_stats['trades'] += 1
        else:
            self.split_stats['trades'] += 1
        
        logger.info(f"⚡ 단타 진입: {signal.symbol} ${signal.current_price:.6f} "
                   f"(${position_size:.2f}, 목표: +{self.quick_exit_threshold:.1%})")
        
        return position
    
    def get_scalping_performance(self) -> Dict:
        """단타 성과 요약"""
        base_stats = super().get_strategy_performance()
        
        scalp_summary = {
            **base_stats,
            'scalping_stats': {
                'total_scalps': self.scalp_stats['total_scalps'],
                'quick_exits': self.scalp_stats['quick_exits'],
                'time_exits': self.scalp_stats['time_exits'],
                'avg_hold_minutes': round(self.scalp_stats['avg_hold_minutes'], 1),
                'quick_exit_rate': (self.scalp_stats['quick_exits'] / max(1, self.scalp_stats['total_scalps'])) * 100
            }
        }
        
        return scalp_summary

    def close_position_scalp(self, symbol: str, current_price: float, 
                           reason: str) -> Optional[Dict]:
        """단타 포지션 청산"""
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        hold_minutes = (datetime.now() - position.entry_time).total_seconds() / 60
        
        # 기본 청산 처리
        trade_record = self.close_position_smart(symbol, current_price, reason)
        
        if trade_record:
            # 단타 정보 추가
            trade_record['hold_minutes'] = round(hold_minutes, 1)
            trade_record['scalping_mode'] = True
            trade_record['exit_type'] = 'scalp_' + reason
            
            # 단타 베스트 기록 업데이트
            pnl = trade_record['pnl_percentage']
            if pnl > self.scalp_stats['best_scalp']:
                self.scalp_stats['best_scalp'] = pnl
            
            logger.info(f"⚡ 단타 완료: {symbol} "
                       f"PnL: {pnl:+.2f}% ({hold_minutes:.1f}분, {reason})")
        
        return trade_record
    
    def get_active_scalps_summary(self) -> Dict:
        """현재 진행중인 단타 요약"""
        if not self.positions:
            return {}
        
        active_scalps = {}
        current_time = datetime.now()
        
        for symbol, position in self.positions.items():
            hold_minutes = (current_time - position.entry_time).total_seconds() / 60
            remaining_minutes = max(0, self.max_hold_minutes - hold_minutes)
            
            active_scalps[symbol] = {
                'entry_price': position.entry_price,
                'hold_minutes': round(hold_minutes, 1),
                'remaining_minutes': round(remaining_minutes, 1),
                'quick_target': getattr(position, 'quick_target', 0),
                'stop_loss': position.stop_loss
            }
        
        return active_scalps
    
    def get_trading_mode(self, portfolio_value: float) -> str:
        """거래 모드 결정"""
        return 'allin' if portfolio_value <= 1000 else 'split'
    
    def should_make_trade(self, portfolio_value: float, current_positions: Dict) -> bool:
        """거래 가능 여부 확인"""
        trading_mode = self.get_trading_mode(portfolio_value)
        
        if trading_mode == 'allin':
            # 올인 모드: 기존 포지션 없을 때만
            return len(current_positions) == 0
        else:
            # 분할 모드: 최대 5개까지
            max_positions = getattr(self.config, 'MAX_POSITIONS_AFTER_SPLIT', 5)
            return len(current_positions) < max_positions
    
    def analyze_best_signal(self, predictions: List[Dict]) -> Optional[Dict]:
        """최고 신호 선택"""
        if not predictions:
            return None
        
        # 확률순으로 이미 정렬되어 있음
        best_signal = predictions[0]
        
        # 단타 최소 확률 체크
        min_prob = getattr(self.config, 'SCALPING_MIN_PROB', 0.65)
        if best_signal['ensemble_probability'] < min_prob:
            return None
        
        return best_signal
    
    def calculate_position_size_smart(self, signal: TradeSignal, available_usdt: float, 
                                    current_positions: Dict) -> float:
        """스마트 포지션 크기 계산"""
        portfolio_value = available_usdt + sum(pos.get('value', 0) for pos in current_positions.values())
        trading_mode = self.get_trading_mode(portfolio_value)
        
        if trading_mode == 'allin':
            # 올인: 95% 투자
            return available_usdt * 0.95
        else:
            # 분할: 20%씩
            return available_usdt * 0.20
    
    def manage_position_smart(self, symbol: str, position: Position, current_price: float) -> Tuple[bool, str]:
        """스마트 포지션 관리 (부모 클래스 메서드 오버라이드)"""
        # 단타 전용 체크 먼저
        should_exit, reason = self.should_quick_exit(position, current_price)
        if should_exit:
            return True, reason
        
        # 기본 청산 조건 체크
        return self.should_exit_position(position, current_price)
    
    def close_position_smart(self, symbol: str, current_price: float, reason: str) -> Optional[Dict]:
        """스마트 포지션 청산"""
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        pnl_data = self.calculate_pnl(position, current_price)
        
        # 거래 기록 생성
        trade_record = {
            'symbol': symbol,
            'entry_price': position.entry_price,
            'exit_price': current_price,
            'quantity': position.quantity,
            'pnl_absolute': pnl_data['pnl_absolute'],
            'pnl_percentage': pnl_data['pnl_percentage'],
            'exit_reason': reason,
            'trading_mode': 'scalping',
            'exit_time': datetime.now().isoformat(),
            'hold_duration_hours': (datetime.now() - position.entry_time).total_seconds() / 3600
        }
        
        # 포지션 제거
        del self.positions[symbol]
        self.save_positions()
        
        return trade_record
