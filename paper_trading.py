"""
페이퍼 트레이딩 엔진 (가상 자금 거래)
"""

from typing import Dict, Optional, List, Tuple
from datetime import datetime
from loguru import logger
import json

from utils import save_json, load_json, ensure_dir

class PaperTradingEngine:
    """가상 자금 거래 엔진"""
    
    def __init__(self, initial_balance: float = 100.0):
        """
        초기화
        Args:
            initial_balance: 초기 USDT 잔고
        """
        self.initial_balance = initial_balance
        self.usdt_balance = initial_balance
        self.positions = {}  # {symbol: {quantity, avg_price, entry_time}}
        self.trade_history = []
        self.portfolio_history = []
        
        # 수수료 설정 (바이낸스 기준)
        self.taker_fee = 0.001  # 0.1%
        self.maker_fee = 0.001  # 0.1%
        
        # 슬리피지 시뮬레이션
        self.slippage_pct = 0.0005  # 0.05%
        
        # 성과 추적
        self.stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_fees_paid': 0.0,
            'max_drawdown': 0.0,
            'peak_value': initial_balance,
            'start_time': datetime.now(),
            'last_update': datetime.now()
        }
        
        # 데이터 저장 경로
        self.data_dir = ensure_dir("paper_trading")
        self.save_state()
        
        logger.info(f"💰 페이퍼 트레이딩 엔진 초기화: ${initial_balance:.2f} USDT")
    
    def get_total_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """현재 포트폴리오 총 가치 계산"""
        total_value = self.usdt_balance
        
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                position_value = position['quantity'] * current_prices[symbol]
                total_value += position_value
            else:
                # 가격 정보가 없으면 입력가 기준으로 계산
                position_value = position['quantity'] * position['avg_price']
                total_value += position_value
        
        return total_value
    
    def can_buy(self, symbol: str, amount_usdt: float) -> bool:
        """매수 가능 여부 확인"""
        # 최소 거래 금액 확인
        if amount_usdt < 5.0:  # 최소 $5
            return False
        
        # 잔고 확인 (수수료 포함)
        required_amount = amount_usdt * (1 + self.taker_fee)
        
        return self.usdt_balance >= required_amount
    
    def can_sell(self, symbol: str, quantity: Optional[float] = None) -> bool:
        """매도 가능 여부 확인"""
        if symbol not in self.positions:
            return False
        
        available_quantity = self.positions[symbol]['quantity']
        
        if quantity is None:
            check_quantity = available_quantity
        else:
            check_quantity = quantity
        
        return check_quantity <= available_quantity and check_quantity > 0
    
    def simulate_slippage(self, price: float, is_buy: bool) -> float:
        """슬리피지 시뮬레이션"""
        if is_buy:
            # 매수시 불리한 방향 (가격 상승)
            return price * (1 + self.slippage_pct)
        else:
            # 매도시 불리한 방향 (가격 하락)
            return price * (1 - self.slippage_pct)
    
    def place_buy_order(self, symbol: str, amount_usdt: float, current_price: float, 
                       strategy_info: Optional[Dict] = None) -> Optional[Dict]:
        """매수 주문 실행"""
        try:
            if not self.can_buy(symbol, amount_usdt):
                logger.warning(f"❌ 매수 불가: {symbol} ${amount_usdt:.2f} (잔고: ${self.usdt_balance:.2f})")
                return None
            
            # 슬리피지 적용
            execution_price = self.simulate_slippage(current_price, True)
            
            # 수수료 계산
            fee_amount = amount_usdt * self.taker_fee
            net_amount = amount_usdt - fee_amount
            
            # 구매 수량 계산
            quantity = net_amount / execution_price
            
            # 기존 포지션이 있으면 평균 단가 계산
            if symbol in self.positions:
                existing_qty = self.positions[symbol]['quantity']
                existing_price = self.positions[symbol]['avg_price']
                existing_value = existing_qty * existing_price
                
                new_total_qty = existing_qty + quantity
                new_avg_price = (existing_value + net_amount) / new_total_qty
                
                self.positions[symbol].update({
                    'quantity': new_total_qty,
                    'avg_price': new_avg_price,
                    'last_update': datetime.now()
                })
            else:
                # 새 포지션 생성
                self.positions[symbol] = {
                    'quantity': quantity,
                    'avg_price': execution_price,
                    'entry_time': datetime.now(),
                    'last_update': datetime.now()
                }
            
            # 잔고 차감
            self.usdt_balance -= amount_usdt
            self.stats['total_fees_paid'] += fee_amount
            
            # 거래 기록
            trade_record = {
                'timestamp': datetime.now().isoformat(),
                'type': 'BUY',
                'symbol': symbol,
                'quantity': quantity,
                'price': execution_price,
                'amount': amount_usdt,
                'fee': fee_amount,
                'balance_after': self.usdt_balance,
                'strategy_info': strategy_info or {}
            }
            
            self.trade_history.append(trade_record)
            self.stats['total_trades'] += 1
            
            logger.info(f"✅ 가상 매수: {symbol} {quantity:.6f} @ ${execution_price:.6f} "
                       f"(총 ${amount_usdt:.2f}, 수수료 ${fee_amount:.2f})")
            
            self.save_state()
            return trade_record
            
        except Exception as e:
            logger.error(f"❌ 매수 주문 실패 {symbol}: {e}")
            return None
    
    def place_sell_order(self, symbol: str, current_price: float, 
                        quantity: Optional[float] = None, strategy_info: Optional[Dict] = None) -> Optional[Dict]:
        """매도 주문 실행"""
        try:
            if not self.can_sell(symbol, quantity):
                logger.warning(f"❌ 매도 불가: {symbol}")
                return None
            
            # 전량 매도가 기본
            if quantity is None:
                sell_quantity = self.positions[symbol]['quantity']
            else:
                sell_quantity = quantity
            
            # 슬리피지 적용
            execution_price = self.simulate_slippage(current_price, False)
            
            # 매도 금액 계산
            gross_amount = sell_quantity * execution_price
            fee_amount = gross_amount * self.taker_fee
            net_amount = gross_amount - fee_amount
            
            # 포지션 정보 가져오기
            position = self.positions[symbol]
            entry_price = position['avg_price']
            entry_time = position['entry_time']
            
            # PnL 계산
            pnl_absolute = (execution_price - entry_price) * sell_quantity
            pnl_percentage = ((execution_price - entry_price) / entry_price) * 100
            
            # 잔고 증가
            self.usdt_balance += net_amount
            self.stats['total_fees_paid'] += fee_amount
            
            # 포지션 업데이트 또는 제거
            if sell_quantity >= position['quantity']:
                # 전량 매도
                del self.positions[symbol]
            else:
                # 부분 매도
                self.positions[symbol]['quantity'] -= sell_quantity
                self.positions[symbol]['last_update'] = datetime.now()
            
            # 승패 기록
            if pnl_absolute > 0:
                self.stats['winning_trades'] += 1
            else:
                self.stats['losing_trades'] += 1
            
            # 거래 기록
            trade_record = {
                'timestamp': datetime.now().isoformat(),
                'type': 'SELL',
                'symbol': symbol,
                'quantity': sell_quantity,
                'price': execution_price,
                'amount': gross_amount,
                'fee': fee_amount,
                'net_amount': net_amount,
                'balance_after': self.usdt_balance,
                'entry_price': entry_price,
                'entry_time': entry_time.isoformat(),
                'pnl_absolute': pnl_absolute,
                'pnl_percentage': pnl_percentage,
                'hold_duration_hours': (datetime.now() - entry_time).total_seconds() / 3600,
                'strategy_info': strategy_info or {}
            }
            
            self.trade_history.append(trade_record)
            self.stats['total_trades'] += 1
            
            logger.info(f"✅ 가상 매도: {symbol} {sell_quantity:.6f} @ ${execution_price:.6f} "
                       f"PnL: {pnl_percentage:+.2f}% (${pnl_absolute:+.2f})")
            
            self.save_state()
            return trade_record
            
        except Exception as e:
            logger.error(f"❌ 매도 주문 실패 {symbol}: {e}")
            return None
    
    def update_portfolio_snapshot(self, current_prices: Dict[str, float]):
        """포트폴리오 스냅샷 업데이트"""
        try:
            total_value = self.get_total_portfolio_value(current_prices)
            
            # 최고점 및 최대 손실 추적
            if total_value > self.stats['peak_value']:
                self.stats['peak_value'] = total_value
            
            drawdown = (self.stats['peak_value'] - total_value) / self.stats['peak_value']
            if drawdown > self.stats['max_drawdown']:
                self.stats['max_drawdown'] = drawdown
            
            # 포트폴리오 스냅샷
            snapshot = {
                'timestamp': datetime.now().isoformat(),
                'total_value': total_value,
                'usdt_balance': self.usdt_balance,
                'total_return': ((total_value - self.initial_balance) / self.initial_balance) * 100,
                'positions': {}
            }
            
            # 각 포지션 상세 정보
            for symbol, position in self.positions.items():
                if symbol in current_prices:
                    current_value = position['quantity'] * current_prices[symbol]
                    unrealized_pnl = ((current_prices[symbol] - position['avg_price']) / position['avg_price']) * 100
                    
                    snapshot['positions'][symbol] = {
                        'quantity': position['quantity'],
                        'avg_price': position['avg_price'],
                        'current_price': current_prices[symbol],
                        'current_value': current_value,
                        'unrealized_pnl_pct': unrealized_pnl,
                        'hold_duration_hours': (datetime.now() - position['entry_time']).total_seconds() / 3600
                    }
            
            self.portfolio_history.append(snapshot)
            self.stats['last_update'] = datetime.now()
            
            # 최근 100개만 유지
            if len(self.portfolio_history) > 100:
                self.portfolio_history = self.portfolio_history[-100:]
            
        except Exception as e:
            logger.error(f"포트폴리오 스냅샷 업데이트 실패: {e}")
    
    def get_performance_summary(self) -> Dict:
        """성과 요약"""
        current_time = datetime.now()
        runtime_hours = (current_time - self.stats['start_time']).total_seconds() / 3600
        
        # 최신 포트폴리오 값
        latest_value = self.portfolio_history[-1]['total_value'] if self.portfolio_history else self.usdt_balance
        total_return_pct = ((latest_value - self.initial_balance) / self.initial_balance) * 100
        
        # 승률 계산
        total_completed_trades = self.stats['winning_trades'] + self.stats['losing_trades']
        win_rate = (self.stats['winning_trades'] / total_completed_trades * 100) if total_completed_trades > 0 else 0
        
        return {
            'initial_balance': self.initial_balance,
            'current_value': latest_value,
            'total_return_pct': total_return_pct,
            'total_return_amount': latest_value - self.initial_balance,
            'runtime_hours': runtime_hours,
            'total_trades': self.stats['total_trades'],
            'winning_trades': self.stats['winning_trades'],
            'losing_trades': self.stats['losing_trades'],
            'win_rate': win_rate,
            'total_fees_paid': self.stats['total_fees_paid'],
            'max_drawdown_pct': self.stats['max_drawdown'] * 100,
            'current_positions': len(self.positions),
            'usdt_balance': self.usdt_balance
        }
    
    def save_state(self):
        """상태 저장"""
        try:
            state_data = {
                'usdt_balance': self.usdt_balance,
                'positions': {
                    symbol: {
                        **position,
                        'entry_time': position['entry_time'].isoformat(),
                        'last_update': position['last_update'].isoformat()
                    }
                    for symbol, position in self.positions.items()
                },
                'stats': {
                    **self.stats,
                    'start_time': self.stats['start_time'].isoformat(),
                    'last_update': self.stats['last_update'].isoformat()
                },
                'trade_history': self.trade_history,
                'portfolio_history': self.portfolio_history
            }
            
            save_json(state_data, str(self.data_dir / "paper_trading_state.json"))
            
        except Exception as e:
            logger.error(f"페이퍼 트레이딩 상태 저장 실패: {e}")
    
    def load_state(self) -> bool:
        """상태 로드"""
        try:
            state_file = self.data_dir / "paper_trading_state.json"
            if not state_file.exists():
                return False
            
            state_data = load_json(str(state_file))
            
            self.usdt_balance = state_data.get('usdt_balance', self.initial_balance)
            self.trade_history = state_data.get('trade_history', [])
            self.portfolio_history = state_data.get('portfolio_history', [])
            
            # 포지션 복원
            positions_data = state_data.get('positions', {})
            self.positions = {}
            
            for symbol, position in positions_data.items():
                self.positions[symbol] = {
                    **position,
                    'entry_time': datetime.fromisoformat(position['entry_time']),
                    'last_update': datetime.fromisoformat(position['last_update'])
                }
            
            # 통계 복원
            stats_data = state_data.get('stats', {})
            if stats_data:
                self.stats.update({
                    **stats_data,
                    'start_time': datetime.fromisoformat(stats_data['start_time']),
                    'last_update': datetime.fromisoformat(stats_data['last_update'])
                })
            
            logger.info(f"📂 페이퍼 트레이딩 상태 로드: 잔고 ${self.usdt_balance:.2f}, "
                       f"포지션 {len(self.positions)}개, 거래 {len(self.trade_history)}회")
            
            return True
            
        except Exception as e:
            logger.error(f"페이퍼 트레이딩 상태 로드 실패: {e}")
            return False

    def get_total_value(self, current_prices: Optional[Dict[str, float]] = None) -> float:
        """총 포트폴리오 가치 반환 (기본 메서드)"""
        if current_prices:
            return self.get_total_portfolio_value(current_prices)
        else:
            # 현재가 정보가 없으면 입력가 기준으로 계산
            total_value = self.usdt_balance
            for symbol, position in self.positions.items():
                position_value = position['quantity'] * position['avg_price']
                total_value += position_value
            return total_value
    
    def execute_buy_order(self, symbol: str, amount_usdt: float, current_price: float) -> Tuple[bool, float, float]:
        """매수 주문 실행 (간소화 버전)"""
        trade_record = self.place_buy_order(symbol, amount_usdt, current_price)
        if trade_record:
            return True, trade_record['quantity'], trade_record['price']
        return False, 0.0, 0.0
    
    def execute_sell_order(self, symbol: str, current_price: float, quantity: Optional[float] = None) -> Tuple[bool, float, float]:
        """매도 주문 실행 (간소화 버전)"""
        trade_record = self.place_sell_order(symbol, current_price, quantity)
        if trade_record:
            return True, trade_record['quantity'], trade_record['price']
        return False, 0.0, 0.0
