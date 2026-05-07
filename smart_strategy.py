"""
🎯 지능형 올인 + 분할 매매 전략

📈 매매 전략:
  • 100만원 이하: 올인 매매 (전체 잔고 투입으로 복리 극대화)
  • 100만원 초과: 분할 매매 (리스크 분산, 최대 5종목)

💰 올인 매매 특징:
  • 시작: 원화 10만원 ($77)
  • 전체 잔고 투입: 잔고의 99.5% 투입 (수수료 0.5% 여유분만)
  • 단일 종목: 가장 유망한 1개 코인에 집중
  • 빠른 회전: 단타 매매로 빠른 복리 증식

🔍 종목 선택:
  • 모든 USDT 페어 스캔 
  • ML 급등 확률 70% 이상 필터링
  • 최고 점수 1개 종목만 선택

⚡ 리스크 관리:
  • -3% 손절 (타이트한 손절)
  • +5% 초기 익절 (올인 시)
  • 1.5% 트레일링 스탑 (이익 극대화)
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from loguru import logger

from trading_strategy import TradingStrategy, Position, TradeSignal

class SmartTradingStrategy(TradingStrategy):
    """지능형 매매 전략 (올인 + 분할)"""
    
    def __init__(self, config):
        super().__init__(config)
        self.config = config
        
        # 전략별 성능 추적
        self.allin_stats = {
            'trades': 0,
            'wins': 0,
            'total_pnl': 0.0
        }
        self.split_stats = {
            'trades': 0,
            'wins': 0,
            'total_pnl': 0.0
        }
    
    def get_trading_mode(self, current_balance: float) -> str:
        """현재 잔고에 따른 매매 모드 결정"""
        if current_balance <= self.config.ALLIN_MAX_BALANCE:  # $700 (원화 100만원) 이하
            return 'allin'  # 올인 매매 - 전체 잔고 투입
        else:
            return 'split'  # 분할 매매 - 포트폴리오 분산
    
    def should_make_trade(self, current_balance: float, current_positions: Dict) -> bool:
        """거래 가능 여부 판단"""
        trading_mode = self.get_trading_mode(current_balance)
        
        if trading_mode == 'allin':
            # 올인 모드: 기존 포지션이 없어야 함
            return len(current_positions) == 0
        else:
            # 분할 모드: 최대 보유 종목 수 미만
            return len(current_positions) < self.config.MAX_POSITIONS_AFTER_SPLIT
    
    def calculate_position_size_smart(self, signal: TradeSignal, 
                                    available_balance: float,
                                    current_positions: Dict) -> float:
        """지능형 포지션 크기 계산"""
        trading_mode = self.get_trading_mode(available_balance)
        
        if trading_mode == 'allin':
            return self._calculate_allin_size(signal, available_balance)
        else:
            return self._calculate_split_size(signal, available_balance, len(current_positions))
    
    def _calculate_allin_size(self, signal: TradeSignal, available_balance: float) -> float:
        """올인 매매 포지션 크기 계산 - 전체 잔고 사용 (100만원 이하)"""
        # BNB 할인 적용된 수수료로 더 적극적인 올인 투자 (99.8%)
        position_size = available_balance * self.config.ALLIN_SAFETY_MARGIN
        
        # BNB 할인 덕분에 더 많은 금액 투입 가능
        logger.info(f"💰 올인 매매 (BNB 할인): ${available_balance:.2f} → ${position_size:.2f} ({(position_size/available_balance)*100:.1f}%)")
        
        # 최소 투자 금액만 체크 (BNB 할인으로 수수료 부담 감소)
        min_size = 6.0   # 최소 $6 (약 8천원)
        
        if position_size < min_size:
            logger.warning(f"⚠️ 잔고 부족: ${available_balance:.2f} < 최소 투자금액 ${min_size}")
            return 0.0

        return position_size
    
    def _calculate_split_size(self, signal: TradeSignal, available_balance: float, 
                            current_positions_count: int) -> float:
        """분할 매매 포지션 크기 계산"""
        # 기본 분할 크기
        base_split_size = available_balance * self.config.MAX_POSITION_SIZE_SPLIT
        
        # 기존 포지션 수에 따른 조정 (포지션이 많을수록 더 보수적)
        position_factor = 1.0 - (current_positions_count * 0.1)
        position_factor = max(0.5, position_factor)
        
        # ML 확률 조정
        prob_multiplier = signal.probability / self.config.ML_PROB_THRESHOLD
        
        position_size = base_split_size * position_factor * prob_multiplier
        
        # 제한
        min_size = 50.0  # 분할 매매시 최소 $50
        max_size = available_balance * 0.25  # 최대 25%
        
        position_size = max(min_size, min(position_size, max_size))
        
        logger.info(f"📊 분할 매매 포지션: ${position_size:.2f} "
                   f"({position_size/available_balance:.1%} of balance, {current_positions_count+1}/5 slots)")
        
        return position_size
    
    def create_stop_loss_take_profit(self, entry_price: float, trading_mode: str) -> Tuple[float, float]:
        """매매 모드별 손절/익절 설정"""
        # 공통: -3% 손절
        stop_loss = entry_price * (1 - self.config.STOP_LOSS_PCT)
        
        if trading_mode == 'allin':
            # 올인 매매: 더 공격적인 익절 (초기 +5% 에서 트레일링 시작)
            take_profit = entry_price * (1 + 0.05)  # 5% 익절
        else:
            # 분할 매매: 보수적 익절 (초기 +8% 에서 트레일링 시작)
            take_profit = entry_price * (1 + 0.08)  # 8% 익절
        
        return stop_loss, take_profit
    
    def update_trailing_stop_smart(self, position: Position, current_price: float, 
                                 trading_mode: str) -> Position:
        """매매 모드별 트레일링 스탑"""
        # 최고가 업데이트 (None 안전 처리)
        if position.highest_price is None or current_price > position.highest_price:
            position.highest_price = current_price
            
            if trading_mode == 'allin':
                # 올인: 더 타이트한 트레일링 (1.5%)
                trailing_pct = 0.015
            else:
                # 분할: 기본 트레일링 (0.8%)
                trailing_pct = self.config.TRAILING_STOP_PCT
            
            new_trailing_stop = current_price * (1 - trailing_pct)
            
            if position.trailing_stop is None or new_trailing_stop > position.trailing_stop:
                position.trailing_stop = new_trailing_stop
                logger.debug(f"{position.symbol} {trading_mode} 트레일링 업데이트: ${new_trailing_stop:.6f}")
        
        return position
    
    def analyze_best_signal(self, all_predictions: List[Dict]) -> Optional[Dict]:
        """모든 예측 결과에서 최고의 신호 1개 선택"""
        if not all_predictions:
            return None
        
        # 유효한 신호들만 필터링
        # 하이브리드 및 ML 신호 필터링 
        valid_signals = []
        for pred in all_predictions:
            if pred.get('signal', False):
                # 하이브리드 신호 (surge_probability 사용)
                if 'surge_probability' in pred:
                    prob = pred.get('surge_probability', 0)
                # 기존 ML 신호 (ensemble_probability 사용)  
                elif 'ensemble_probability' in pred:
                    prob = pred.get('ensemble_probability', 0)
                else:
                    prob = 0
                    
                if prob >= self.config.ML_PROB_THRESHOLD:
                    valid_signals.append(pred)
        
        if not valid_signals:
            logger.info("💤 유효한 급등 신호 없음")
            return None
        
        # 확률 * 신뢰도 점수로 정렬 (하이브리드 지원)
        def calculate_score(prediction):
            # 하이브리드 신호는 surge_probability, ML 신호는 ensemble_probability 사용
            if 'surge_probability' in prediction:
                prob = prediction.get('surge_probability', 0)
            else:
                prob = prediction.get('ensemble_probability', 0)
                
            confidence = prediction.get('confidence', 'low')
            
            confidence_multiplier = {
                'high': 1.2,
                'medium': 1.0,
                'low': 0.8
            }.get(confidence, 0.8)
            
            return prob * confidence_multiplier
        
        # 점수순 정렬
        valid_signals.sort(key=calculate_score, reverse=True)
        
        best_signal = valid_signals[0]
        score = calculate_score(best_signal)
        
        # 하이브리드와 ML 신호 모두 지원하는 확률 표시
        if 'surge_probability' in best_signal:
            prob = best_signal['surge_probability']
            signal_type = "하이브리드"
        else:
            prob = best_signal['ensemble_probability']
            signal_type = "ML"
            
        logger.info(f"🎯 최고 신호 선택: {best_signal['symbol']} "
                   f"(확률: {prob:.2%}, "
                   f"신뢰도: {best_signal['confidence']}, 점수: {score:.3f}, 타입: {signal_type})")
        
        return best_signal
    
    def execute_smart_trade(self, best_prediction: Dict, current_balance: float, 
                          current_positions: Dict) -> Optional[Position]:
        """지능형 매매 실행"""
        if not self.should_make_trade(current_balance, current_positions):
            return None
        
        # 거래 신호 생성
        signal = self.analyze_signal(best_prediction, current_positions)
        
        if signal.action != 'buy':
            return None
        
        # 매매 모드 결정
        trading_mode = self.get_trading_mode(current_balance)
        
        # 포지션 크기 계산
        position_size = self.calculate_position_size_smart(
            signal, current_balance, current_positions
        )
        
        if position_size < 10:  # 최소 거래 금액
            return None
        
        # 손절/익절 계산
        stop_loss, take_profit = self.create_stop_loss_take_profit(
            signal.current_price, trading_mode
        )
        
        # 포지션 생성
        position = Position(
            symbol=signal.symbol,
            entry_price=signal.current_price,
            quantity=position_size / signal.current_price,  # 수량 계산
            entry_time=signal.timestamp,
            stop_loss=stop_loss,
            take_profit=take_profit,
            highest_price=signal.current_price,
            entry_reason=f"{trading_mode}_{signal.confidence}_{signal.probability:.3f}"
        )
        
        # 포지션 저장
        self.positions[signal.symbol] = position
        self.save_positions()
        
        # 통계 업데이트
        if trading_mode == 'allin':
            self.allin_stats['trades'] += 1
        else:
            self.split_stats['trades'] += 1
        
        logger.info(f"✅ {trading_mode.upper()} 매매 진입: {signal.symbol} "
                   f"${signal.current_price:.6f} (포지션: ${position_size:.2f})")
        
        return position
    
    def manage_position_smart(self, symbol: str, position: Position, 
                            current_price: float) -> Tuple[bool, str]:
        """지능형 포지션 관리"""
        # 매매 모드 확인
        trading_mode = 'allin' if 'allin' in position.entry_reason else 'split'
        
        # 트레일링 스탑 업데이트
        position = self.update_trailing_stop_smart(position, current_price, trading_mode)
        self.positions[symbol] = position
        
        # 청산 조건 확인 (부모 클래스 메서드 사용)
        should_exit, exit_reason = self.should_exit_position(position, current_price)
        
        return should_exit, exit_reason
    
    def close_position_smart(self, symbol: str, current_price: float, 
                           reason: str) -> Optional[Dict]:
        """지능형 포지션 청산"""
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        trading_mode = 'allin' if 'allin' in position.entry_reason else 'split'
        
        # PnL 계산 및 청산 처리
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
        
        if trade_record:
            # 매매 모드별 통계 업데이트
            pnl = trade_record['pnl_absolute']
            
            if trading_mode == 'allin':
                self.allin_stats['total_pnl'] += pnl
                if pnl > 0:
                    self.allin_stats['wins'] += 1
            else:
                self.split_stats['total_pnl'] += pnl
                if pnl > 0:
                    self.split_stats['wins'] += 1
            
            # 매매 기록에 모드 추가
            trade_record['trading_mode'] = trading_mode
            
            logger.info(f"💰 {trading_mode.upper()} 청산: {symbol} "
                       f"PnL: {trade_record['pnl_percentage']:+.2f}% ({reason})")
        
        return trade_record
    
    def get_strategy_performance(self) -> Dict:
        """전략별 성능 요약"""
        allin_winrate = (self.allin_stats['wins'] / max(1, self.allin_stats['trades'])) * 100
        split_winrate = (self.split_stats['wins'] / max(1, self.split_stats['trades'])) * 100
        
        return {
            'allin_strategy': {
                'trades': self.allin_stats['trades'],
                'wins': self.allin_stats['wins'],
                'win_rate': allin_winrate,
                'total_pnl': self.allin_stats['total_pnl'],
                'avg_pnl_per_trade': self.allin_stats['total_pnl'] / max(1, self.allin_stats['trades'])
            },
            'split_strategy': {
                'trades': self.split_stats['trades'],
                'wins': self.split_stats['wins'], 
                'win_rate': split_winrate,
                'total_pnl': self.split_stats['total_pnl'],
                'avg_pnl_per_trade': self.split_stats['total_pnl'] / max(1, self.split_stats['trades'])
            },
            'combined': {
                'total_trades': self.allin_stats['trades'] + self.split_stats['trades'],
                'total_wins': self.allin_stats['wins'] + self.split_stats['wins'],
                'overall_pnl': self.allin_stats['total_pnl'] + self.split_stats['total_pnl']
            }
        }
