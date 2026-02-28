"""
거래 전략 및 포지션 관리
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from loguru import logger
import json

from utils import log_trade, log_signal, save_json, load_json, calculate_percentage_change

@dataclass
class Position:
    """포지션 정보"""
    symbol: str
    entry_price: float
    quantity: float
    entry_time: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_stop: Optional[float] = None
    highest_price: Optional[float] = None
    entry_reason: str = "ML_signal"
    quick_target: Optional[float] = None

@dataclass 
class TradeSignal:
    """거래 신호"""
    symbol: str
    action: str
    probability: float
    confidence: str
    current_price: float
    reasons: List[str]
    timestamp: datetime

class TradingStrategy:
    """머신러닝 기반 거래 전략"""
    
    def __init__(self, config):
        self.config = config
        self.positions = {}
        self.trade_history = []
        self.performance_stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'max_drawdown': 0.0
        }
        
        self.confidence_thresholds = {
            'high': 0.8,
            'medium': 0.6,
            'low': 0.4
        }
        
        logger.info("📊 거래 전략 초기화 완료")
    
    def analyze_signal(self, prediction: Dict, current_positions: Dict) -> TradeSignal:
        """예측 결과를 거래 신호로 변환 (하이브리드 지원)"""
        symbol = prediction['symbol']
        
        # 하이브리드 신호는 surge_probability, ML 신호는 ensemble_probability 사용
        if 'surge_probability' in prediction:
            probability = prediction['surge_probability']
        else:
            probability = prediction['ensemble_probability']
            
        current_price = prediction['current_price']
        
        if probability >= self.confidence_thresholds['high']:
            confidence = 'high'
        elif probability >= self.confidence_thresholds['medium']:
            confidence = 'medium'
        else:
            confidence = 'low'
        
        if probability >= self.config.ML_PROB_THRESHOLD and symbol not in current_positions:
            action = 'buy'
            reasons = [f'ML 확률: {probability:.2%}', f'신뢰도: {confidence}']
        else:
            action = 'hold'
            reasons = ['조건 미달']
        
        return TradeSignal(
            symbol=symbol,
            action=action,
            probability=probability,
            confidence=confidence,
            current_price=current_price,
            reasons=reasons,
            timestamp=datetime.now()
        )
    
    def should_exit_position(self, position: Position, current_price: float) -> Tuple[bool, str]:
        """포지션 청산 조건 확인"""
        if position.stop_loss is not None and current_price <= position.stop_loss:
            return True, "stop_loss"
        
        if position.take_profit is not None and current_price >= position.take_profit:
            return True, "take_profit"
        
        if position.trailing_stop is not None and current_price <= position.trailing_stop:
            return True, "trailing_stop"
        
        if datetime.now() - position.entry_time > timedelta(hours=24):
            return True, "time_exit"
        
        return False, ""
    
    def calculate_pnl(self, position: Position, current_price: float) -> Dict[str, float]:
        """PnL 계산"""
        pnl_absolute = (current_price - position.entry_price) * position.quantity
        pnl_percentage = ((current_price - position.entry_price) / position.entry_price) * 100
        
        return {
            'pnl_absolute': pnl_absolute,
            'pnl_percentage': pnl_percentage,
            'unrealized_pnl': pnl_absolute
        }
    
    def save_positions(self):
        """포지션 저장"""
        try:
            positions_data = {}
            for symbol, position in self.positions.items():
                positions_data[symbol] = {
                    'symbol': position.symbol,
                    'entry_price': position.entry_price,
                    'quantity': position.quantity,
                    'entry_time': position.entry_time.isoformat(),
                    'stop_loss': position.stop_loss,
                    'take_profit': position.take_profit,
                    'trailing_stop': position.trailing_stop,
                    'highest_price': position.highest_price,
                    'entry_reason': position.entry_reason,
                    'quick_target': getattr(position, 'quick_target', None)
                }
            
            save_json(positions_data, "data/positions.json")
            
        except Exception as e:
            logger.error(f"포지션 저장 실패: {e}")
    
    def close_position(self, symbol: str, current_price: float, reason: str) -> Optional[Dict]:
        """포지션 청산"""
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        
        # PnL 계산
        pnl_data = self.calculate_pnl(position, current_price)
        
        # 거래 기록 생성
        trade_record = {
            'symbol': symbol,
            'entry_price': position.entry_price,
            'exit_price': current_price,
            'quantity': position.quantity,
            'entry_time': position.entry_time.isoformat(),
            'exit_time': datetime.now().isoformat(),
            'pnl_absolute': pnl_data['pnl_absolute'],
            'pnl_percentage': pnl_data['pnl_percentage'],
            'exit_reason': reason,
            'entry_reason': position.entry_reason
        }
        
        # 포지션 제거
        del self.positions[symbol]
        self.save_positions()
        
        # 성능 통계 업데이트
        self.performance_stats['total_trades'] += 1
        self.performance_stats['total_pnl'] += pnl_data['pnl_absolute']
        
        if pnl_data['pnl_absolute'] > 0:
            self.performance_stats['winning_trades'] += 1
        else:
            self.performance_stats['losing_trades'] += 1
        
        self.trade_history.append(trade_record)
        
        return trade_record

    def get_performance_summary(self) -> Dict:
        """성능 요약"""
        total_trades = self.performance_stats['total_trades']
        winning_trades = self.performance_stats['winning_trades']
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': self.performance_stats['losing_trades'],
            'win_rate': win_rate,
            'total_pnl': self.performance_stats['total_pnl'],
            'max_drawdown': self.performance_stats['max_drawdown'],
            'active_positions': len(self.positions)
        }