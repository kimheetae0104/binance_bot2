#!/usr/bin/env python3
"""
페이퍼 트레이딩 전용 메인 봇
24시간 자동 가상 매매 시스템
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import traceback
from loguru import logger

from config import load_config
from binance_api import BinanceConnector
from ml_predictor import MLPredictor  # 실제 ML 예측기 사용
from smart_strategy import SmartTradingStrategy
from telegram_notifier import TelegramNotifier
from dashboard import TradingDashboard
from paper_trading import PaperTradingEngine
from trading_strategy import Position
from utils import ensure_dir, save_json, load_json
from hybrid_surge_detector import HybridSurgeDetector, detect_surge_opportunities_async

class PaperTradingBot:
    """페이퍼 트레이딩 전용 봇"""
    
    def __init__(self):
        # 설정 로드
        self.config = load_config()
        
        # 컴포넌트 초기화
        self.binance = BinanceConnector(self.config)  # 시장 데이터용만
        self.ml_predictor = MLPredictor(self.config)  # 실제 ML 예측기 사용
        self.strategy = SmartTradingStrategy(self.config)  # 스마트 전략 사용
        self.dashboard = TradingDashboard()
        self.notifier = TelegramNotifier(
            self.config.TELEGRAM_BOT_TOKEN, 
            self.config.TELEGRAM_CHAT_ID
        )
        
        # 페이퍼 트레이딩 엔진 초기화 (70 USDT = ~10만원)
        self.paper_trading = PaperTradingEngine(initial_balance=70.0)
        
        # 상태 관리
        self.is_running = False
        self.scan_symbols = []
        self.last_model_training = None
        self.performance_data = {
            'start_time': datetime.now(),
            'total_signals': 0,
            'executed_trades': 0,
            'scan_cycles': 0
        }
        
        # 디렉토리 생성
        ensure_dir("data")
        ensure_dir("models")
        ensure_dir("logs")
        
        logger.info("🤖 페이퍼 트레이딩 봇 초기화 완료")
    
    def safe_send_telegram(self, message: str):
        """안전한 텔레그램 전송 (타임아웃 방지)"""
        try:
            success = self.notifier.send_message_safe(message)
            if not success:
                logger.warning("⚠️ 텔레그램 전송 실패 (계속 진행)")
        except Exception as e:
            logger.warning(f"⚠️ 텔레그램 전송 오류 (무시됨): {e}")
    
    async def initialize(self):
        """봇 초기화"""
        try:
            logger.info("🚀 페이퍼 트레이딩 봇 초기화 시작...")
            
            # 페이퍼 트레이딩 상태 로드
            self.paper_trading.load_state()
            
            # 거래 가능한 심볼 조회
            self.scan_symbols = self.binance.get_usdt_pairs(
                min_volume=self.config.MIN_USDT_24H_VOLUME
            )
            
            if not self.scan_symbols:
                logger.error("❌ 스캔할 심볼이 없습니다")
                return False
            
            logger.info(f"📊 스캔 대상: {len(self.scan_symbols)}개 심볼")
            
            # ML 모델 로드 또는 자동 훈련
            model_loaded = self.ml_predictor.load_models()
            
            if not model_loaded:
                logger.info("🧠 ML 모델이 없어서 자동으로 새로 훈련합니다...")
                self.safe_send_telegram("🧠 ML 모델이 없어서 자동 훈련을 시작합니다...")
                
                # 자동 모델 훈련 실행
                await self.train_models()
                
                # 훈련 완료 후 다시 로드 시도
                model_loaded = self.ml_predictor.load_models()
                
                if not model_loaded:
                    logger.error("❌ 자동 모델 훈련 후에도 로드 실패")
                    self.safe_send_telegram("❌ 자동 ML 훈련 실패. 봇을 재시작해주세요.")
                    return False
                else:
                    logger.info("✅ 자동 ML 모델 훈련 및 로드 성공!")
                    self.safe_send_telegram("✅ ML 모델 자동 훈련 완료! 트레이딩 시작합니다.")
            
            # 시작 알림
            await self.send_startup_notification()
            
            self.is_running = True
            logger.info("✅ 페이퍼 트레이딩 봇 초기화 완료!")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 초기화 실패: {e}")
            traceback.print_exc()
            return False
    
    async def train_models(self):
        """ML 모델 훈련 - 완전 자동화"""
        try:
            logger.info("🧠 ML 모델 자동 훈련 시작...")
            self.safe_send_telegram("🧠 ML 모델 자동 훈련을 시작합니다...")
            
            # 1단계: 훈련 데이터 수집 (상위 100개 심볼로 확장)
            training_symbols = self.scan_symbols[:100]
            logger.info(f"📊 훈련 데이터 수집 중: {len(training_symbols)}개 심볼")
            
            # 여러 번 시도하여 안정적으로 데이터 수집
            training_data = None
            for attempt in range(3):  # 최대 3번 시도
                try:
                    training_data = self.ml_predictor.collect_training_data(
                        self.binance, training_symbols
                    )
                    
                    if training_data is not None and len(training_data) > 100:
                        logger.info(f"✅ 훈련 데이터 수집 성공: {len(training_data)}개 샘플")
                        break
                    else:
                        logger.warning(f"⚠️ 시도 {attempt + 1}: 데이터 부족 ({len(training_data) if training_data is not None else 0}개)")
                        
                except Exception as e:
                    logger.warning(f"⚠️ 시도 {attempt + 1} 실패: {e}")
                    if attempt < 2:  # 마지막 시도가 아니면 잠시 대기
                        await asyncio.sleep(5)
            
            # 2단계: 모델 훈련 실행
            if training_data is not None and len(training_data) > 100:
                logger.info("🎯 ML 모델 훈련 실행...")
                success = self.ml_predictor.train_models(training_data)
                
                if success:
                    self.last_model_training = datetime.now()
                    self.safe_send_telegram("✅ ML 모델 자동 훈련 완료!")
                    logger.info("✅ ML 모델 자동 훈련 성공")
                    return True
                else:
                    self.safe_send_telegram("❌ ML 모델 훈련 실행 실패")
                    logger.error("❌ ML 모델 훈련 실행 실패")
            else:
                # 3단계: 폴백 - 기본 모델 생성
                logger.warning("⚠️ 훈련 데이터 부족, 기본 모델 생성 시도...")
                self.safe_send_telegram("⚠️ 훈련 데이터 부족, 기본 모델로 시작합니다.")
                
                # 최소한의 더미 모델이라도 생성하여 시스템이 동작하도록
                try:
                    basic_symbols = training_symbols[:20]  # 상위 20개만
                    basic_data = self.ml_predictor.collect_training_data(
                        self.binance, basic_symbols
                    )
                    
                    if basic_data is not None and len(basic_data) > 50:
                        success = self.ml_predictor.train_models(basic_data)
                        if success:
                            logger.info("✅ 기본 모델 생성 성공")
                            self.last_model_training = datetime.now()
                            return True
                except Exception as e:
                    logger.error(f"❌ 기본 모델 생성도 실패: {e}")
                
                self.safe_send_telegram("❌ 모든 훈련 방법 실패")
                logger.error("❌ 모든 모델 훈련 방법 실패")
            
            return False
                
        except Exception as e:
            logger.error(f"❌ 모델 훈련 전체 실패: {e}")
            self.safe_send_telegram(f"❌ 모델 훈련 전체 실패: {e}")
            return False
    
    async def send_startup_notification(self):
        """시작 알림"""
        portfolio_value = self.paper_trading.get_total_value()
        message = f"""⚡ 하이브리드 페이퍼 트레이딩 봇 시작
        
💰 초기 포트폴리오: ${portfolio_value:.2f}
📊 스캔 심볼: {len(self.scan_symbols)}개
🎯 매매 모드: {'올인' if portfolio_value <= 1000 else '분할'}
⚡ 하이브리드 전략:
  - 손절선: -{self.config.STOP_LOSS_PCT:.1%}
  - 트레일링 익절: 신고가 갱신 추적 후 하락시 익절
    · 올인: 신고가 대비 -1.5% 하락시
    · 분할: 신고가 대비 -0.8% 하락시
  - 최대 보유: 무제한 (계속 상승시 계속 보유)
  - ML 임계값: {self.config.ML_PROB_THRESHOLD:.0%}
  - 급등 감지: 실시간 모멘텀
  - 스캔 간격: 2분
⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

        self.safe_send_telegram(message)
        logger.info("📢 하이브리드 봇 시작 알림 전송 완료")
    
    async def scan_market(self) -> List[Dict]:
        """하이브리드 시장 스캔 - 급등 감지 + ML 예측"""
        try:
            logger.info("🔍 하이브리드 시장 스캔 시작...")
            
            # 1단계: 하이브리드 급등 감지 (실시간 모멘텀)
            surge_signals = await detect_surge_opportunities_async(
                self.scan_symbols,
                binance=self.binance,
                ml_predictor=self.ml_predictor,
            )
            logger.info(f"⚡ 급등 신호 감지: {len(surge_signals)}개")
            
            # 2단계: 급등 신호를 ML 예측 형태로 변환
            predictions = []
            
            for signal in surge_signals:
                try:
                    symbol = signal['symbol']
                    signal_type = signal.get('signal_type', 'surge')
                    hybrid_score = signal.get('hybrid_score', 0)
                    
                    # 하이브리드 신호를 예측 형태로 변환
                    prediction = {
                        'symbol': symbol,
                        'signal': True,
                        'surge_probability': hybrid_score,
                        'confidence': 'high' if hybrid_score > 0.7 else 'medium',
                        'current_price': signal.get('current_price', 0),
                        'signal_type': f"hybrid_{signal_type}",
                        'price_change_5m': signal.get('price_change_5m', 0),
                        'price_change_1h': signal.get('price_change_1h', 0),
                        'volume_ratio': signal.get('volume_ratio', 1.0)
                    }
                    
                    predictions.append(prediction)
                    logger.info(f"🎯 하이브리드 신호: {symbol} ({hybrid_score:.1%}) [{signal_type}]")
                    
                except Exception as e:
                    logger.warning(f"❌ {signal.get('symbol', 'Unknown')} 신호 변환 실패: {e}")
                    continue
            
            # 3단계: ML로 추가 검증 (하이브리드가 놓친 것들)
            if len(predictions) < 5:  # 급등 신호가 적으면 ML로 보완
                logger.info("🧠 ML 보완 스캔 시작...")
                
                # 이미 급등 감지된 심볼들 제외
                detected_symbols = set(p['symbol'] for p in predictions)
                remaining_symbols = [s for s in self.scan_symbols if s not in detected_symbols]
                
                # 상위 20개만 ML 스캔 (시간 단축)
                ml_symbols = remaining_symbols[:20]
                
                for symbol in ml_symbols:
                    try:
                        result = self.ml_predictor.predict_symbol(self.binance, symbol)
                        
                        if result and result.get('signal', False):
                            # ML 신호 표시
                            result['signal_type'] = 'ml_only'
                            predictions.append(result)
                            logger.info(f"🧠 ML 신호: {symbol} ({result['surge_probability']:.2%})")
                        
                    except Exception as e:
                        continue
                
                await asyncio.sleep(0.1)  # API 제한 대응
            
            # 확률순 정렬 (하이브리드 우선)
            predictions.sort(key=lambda x: (
                1 if x.get('signal_type', '').startswith('hybrid') else 0,  # 하이브리드 우선
                x.get('surge_probability', 0)  # 확률순
            ), reverse=True)
            
            logger.info(f"📈 총 신호 발견: {len(predictions)}개 (하이브리드: {len(surge_signals)}개, ML: {len(predictions) - len(surge_signals)}개)")
            self.performance_data['total_signals'] += len(predictions)
            self.performance_data['scan_cycles'] += 1
            
            return predictions
            
        except Exception as e:
            logger.error(f"❌ 하이브리드 스캔 오류: {e}")
            # 폴백: 기존 ML만 사용
            return await self._fallback_ml_scan()
    
    async def _fallback_ml_scan(self) -> List[Dict]:
        """하이브리드 실패시 ML 전용 스캔"""
        try:
            logger.warning("⚠️ 하이브리드 실패, ML 전용 스캔으로 폴백")
            predictions = []
            
            for symbol in self.scan_symbols[:30]:  # 상위 30개만
                try:
                    result = self.ml_predictor.predict_symbol(self.binance, symbol)
                    if result and result.get('signal', False):
                        predictions.append(result)
                except:
                    continue
            
            return predictions
            
        except Exception as e:
            logger.error(f"❌ 폴백 스캔 실패: {e}")
            return []
    
    async def execute_paper_trade(self, predictions: List[Dict]):
        """페이퍼 트레이딩 실행"""
        try:
            if not predictions:
                logger.info("💤 거래할 신호가 없습니다")
                return
            
            # 현재 포트폴리오 상태
            portfolio_value = self.paper_trading.get_total_value()
            available_usdt = self.paper_trading.usdt_balance
            current_positions = self.paper_trading.positions
            
            logger.info(f"💰 페이퍼 포트폴리오: ${portfolio_value:.2f} (현금: ${available_usdt:.2f})")
            
            if available_usdt < 10:
                logger.warning("⚠️ 가용 현금 부족으로 거래를 건너뜁니다")
                return
            
            # 거래 모드 확인
            trading_mode = self.strategy.get_trading_mode(portfolio_value)
            logger.info(f"📊 현재 모드: {trading_mode.upper()}")
            
            # 거래 가능 여부 확인
            if not self.strategy.should_make_trade(portfolio_value, current_positions):
                if trading_mode == 'allin':
                    logger.info("💤 올인 모드: 기존 포지션 보유 중으로 대기")
                else:
                    logger.info(f"💤 분할 모드: 최대 포지션 수 도달 ({len(current_positions)}/{self.config.MAX_POSITIONS_AFTER_SPLIT})")
                return
            
            # 최고의 신호 선택
            best_prediction = self.strategy.analyze_best_signal(predictions)
            
            if not best_prediction:
                logger.info("💤 거래 가능한 신호 없음")
                return
            
            symbol = best_prediction['symbol']
            current_price = best_prediction['current_price']
            
            # 이미 보유 중인지 확인
            if symbol in current_positions:
                logger.info(f"📊 {symbol} 이미 보유 중으로 스킵")
                return
            
            try:
                # 포지션 크기 계산
                signal = self.strategy.analyze_signal(best_prediction, current_positions)
                position_size = self.strategy.calculate_position_size_smart(
                    signal, available_usdt, current_positions
                )
                
                if position_size < 10:
                    logger.warning("⚠️ 포지션 크기가 너무 작아 거래를 건너뜁니다")
                    return
                
                # 스마트 매수 실행
                trade_record = self.paper_trading.place_buy_order(
                    symbol, position_size, current_price,
                    strategy_info={
                        'trading_mode': 'smart_' + trading_mode,
                        'probability': best_prediction['surge_probability'],
                        'confidence': best_prediction['confidence'],
                        'expected_hold_hours': 4  # 최대 4시간
                    }
                )
                
                if trade_record:
                    # 스마트 전략 포지션 생성 (무제한 상승 허용)
                    stop_loss = current_price * (1 - self.config.STOP_LOSS_PCT)
                    take_profit = None  # 하이브리드에서는 트레일링 스탑만 사용
                    
                    position = Position(
                        symbol=symbol,
                        entry_price=trade_record['price'],
                        quantity=trade_record['quantity'],
                        entry_time=datetime.now(),
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        highest_price=trade_record['price'],
                        entry_reason=f"hybrid_{trading_mode}_{best_prediction['confidence']}"
                    )
                    
                    # 포지션 저장
                    self.strategy.positions[symbol] = position
                    self.strategy.save_positions()
                    
                    # 대시보드에 매수 기록 저장
                    buy_record = {
                        'symbol': symbol,
                        'side': 'buy',
                        'type': 'entry',
                        'quantity': trade_record['quantity'],
                        'price': trade_record['price'],
                        'value': trade_record['quantity'] * trade_record['price'],
                        'timestamp': datetime.now().isoformat(),
                        'trading_mode': trading_mode,
                        'probability': best_prediction['surge_probability'],
                        'confidence': best_prediction['confidence']
                    }
                    self.dashboard.update_trade_record(buy_record)
                    
                    # 통계 업데이트
                    if trading_mode == 'allin':
                        self.strategy.allin_stats['trades'] += 1
                    else:
                        self.strategy.split_stats['trades'] += 1
                    
                    # 텔레그램 알림
                    self.notifier.send_trade_entry(
                        symbol, trade_record['price'], trade_record['quantity'],
                        best_prediction['surge_probability'], 
                        best_prediction['confidence'], position_size
                    )
                    
                    logger.info(f"✅ 페이퍼 {trading_mode.upper()} 매수: {symbol} "
                               f"${trade_record['price']:.6f} x {trade_record['quantity']:.6f} (${position_size:.2f})")
                    
                    self.performance_data['executed_trades'] += 1
                else:
                    logger.warning(f"❌ {symbol} 페이퍼 매수 실패")
                    
            except Exception as e:
                logger.error(f"❌ {symbol} 거래 실행 실패: {e}")
                
        except Exception as e:
            logger.error(f"❌ 페이퍼 거래 실행 오류: {e}")
            traceback.print_exc()
    
    async def manage_paper_positions(self):
        """페이퍼 포지션 관리"""
        try:
            # 보유 중인 포지션이 없으면 스킵
            if not self.paper_trading.positions:
                return
            
            logger.info(f"📊 포지션 관리: {len(self.paper_trading.positions)}개")
            
            # 현재가 조회
            symbols = list(self.paper_trading.positions.keys())
            current_prices = {}
            
            for symbol in symbols:
                try:
                    price = self.binance.get_current_price(symbol)
                    if price:
                        current_prices[symbol] = price
                except Exception as e:
                    logger.warning(f"❌ {symbol} 현재가 조회 실패: {e}")
            
            # 포트폴리오 스냅샷 업데이트
            self.paper_trading.update_portfolio_snapshot(current_prices)
            
            # 각 포지션 관리
            for symbol in list(self.paper_trading.positions.keys()):
                if symbol not in current_prices:
                    continue
                
                try:
                    paper_pos = self.paper_trading.positions[symbol]
                    current_price = current_prices[symbol]
                    
                    # 전략 포지션 동기화
                    if symbol not in self.strategy.positions:
                        # 페이퍼 포지션 기반으로 전략 포지션 생성
                        position = Position(
                            symbol=symbol,
                            entry_price=paper_pos['avg_price'],
                            quantity=paper_pos['quantity'],
                            entry_time=paper_pos['entry_time'],
                            entry_reason="paper_sync"
                        )
                        self.strategy.positions[symbol] = position
                    
                    position = self.strategy.positions[symbol]
                    trading_mode = 'allin' if 'allin' in position.entry_reason else 'split'
                    
                    # 단타 포지션 관리 (빠른 익절 포함)
                    should_exit, exit_reason = self.strategy.manage_position_smart(
                        symbol, position, current_price
                    )
                    
                    if should_exit:
                        # 페이퍼 매도 실행
                        trade_record = self.paper_trading.place_sell_order(
                            symbol, current_price,
                            strategy_info={
                                'exit_reason': exit_reason,
                                'trading_mode': trading_mode
                            }
                        )
                        
                        if trade_record:
                            # 전략 포지션 청산
                            strategy_trade = self.strategy.close_position_smart(
                                symbol, trade_record['price'], exit_reason
                            )
                            
                            if strategy_trade:
                                # 대시보드에 매도 기록 저장
                                sell_record = {
                                    'symbol': symbol,
                                    'side': 'sell',
                                    'type': 'exit',
                                    'quantity': trade_record['quantity'],
                                    'price': trade_record['price'],
                                    'value': trade_record['quantity'] * trade_record['price'],
                                    'timestamp': datetime.now().isoformat(),
                                    'trading_mode': trading_mode,
                                    'exit_reason': exit_reason,
                                    'profit': trade_record.get('pnl_absolute', 0),
                                    'profit_pct': trade_record.get('pnl_percentage', 0),
                                    'hold_time_hours': trade_record.get('hold_duration_hours', 0)
                                }
                                self.dashboard.update_trade_record(sell_record)
                                
                                # 전략 거래 기록도 저장
                                if strategy_trade:
                                    self.dashboard.update_trade_record(strategy_trade)
                                
                                # 텔레그램 알림
                                self.notifier.send_trade_exit(
                                    symbol, paper_pos['avg_price'], trade_record['price'],
                                    trade_record['quantity'], trade_record['pnl_percentage'], 
                                    trade_record['pnl_absolute'], exit_reason, 
                                    trade_record['hold_duration_hours']
                                )
                                
                                logger.info(f"🏁 페이퍼 {trading_mode.upper()} 매도: {symbol} "
                                           f"PnL: {trade_record['pnl_percentage']:+.2f}% ({exit_reason})")
                        else:
                            logger.warning(f"❌ {symbol} 페이퍼 매도 실패")
                    
                except Exception as e:
                    logger.error(f"❌ {symbol} 포지션 관리 실패: {e}")
                    
        except Exception as e:
            logger.error(f"❌ 포지션 관리 오류: {e}")
    
    async def update_dashboard(self):
        """대시보드 업데이트"""
        try:
            portfolio_value = self.paper_trading.get_total_value()
            
            # 현재가 정보를 포함한 포지션 데이터 준비
            positions_list = []
            if self.paper_trading.positions:
                for symbol, position in self.paper_trading.positions.items():
                    try:
                        current_price = self.binance.get_current_price(symbol)
                        
                        # 포지션 데이터를 딕셔너리 형태로 구성
                        pos_data = {
                            'symbol': symbol,
                            'entry_price': position.get('avg_price', 0),
                            'current_price': current_price,
                            'quantity': position.get('quantity', 0),
                            'entry_time': position.get('entry_time', datetime.now().isoformat()),
                            'side': 'buy'  # 페이퍼 트레이딩에서는 보통 매수 포지션
                        }
                        
                        positions_list.append(pos_data)
                        logger.info(f"📊 포지션 추가: {symbol} - 진입가: {pos_data['entry_price']}, 현재가: {current_price}")
                        
                    except Exception as e:
                        logger.warning(f"❌ {symbol} 현재가 조회 실패: {e}")
                        # 현재가를 구하지 못해도 진입가라도 표시
                        pos_data = {
                            'symbol': symbol,
                            'entry_price': position.get('avg_price', 0),
                            'current_price': position.get('avg_price', 0),
                            'quantity': position.get('quantity', 0),
                            'entry_time': position.get('entry_time', datetime.now().isoformat()),
                            'side': 'buy'
                        }
                        positions_list.append(pos_data)
            
            # 대시보드 데이터 생성 (포트폴리오 총 가치가 아닌 현금 잔고 전달)
            dashboard_data = self.dashboard.generate_dashboard_data(
                current_balance=self.paper_trading.usdt_balance,  # 실제 현금 잔고
                positions=positions_list,
                trading_mode="paper",
                ml_confidence=getattr(self, 'last_ml_confidence', 0.0),
                last_signal=getattr(self, 'last_signal', 'none')
            )
            
            if dashboard_data:
                # 성과 데이터에 페이퍼 트레이딩 정보 추가
                dashboard_data['paper_trading'] = {
                    'total_value': portfolio_value,
                    'usdt_balance': self.paper_trading.usdt_balance,
                    'total_return_pct': ((portfolio_value - self.paper_trading.initial_balance) / self.paper_trading.initial_balance) * 100,
                    'total_trades': self.paper_trading.stats['total_trades'],
                    'win_rate': (self.paper_trading.stats['winning_trades'] / max(1, self.paper_trading.stats['total_trades'])) * 100,
                    'fees_paid': self.paper_trading.stats['total_fees_paid'],
                    'max_drawdown': self.paper_trading.stats['max_drawdown'] * 100
                }
                
                # 스냅샷 저장
                self.dashboard.save_dashboard_snapshot(dashboard_data)
                
            logger.info("📊 대시보드 업데이트 완료")
            
        except Exception as e:
            logger.error(f"❌ 대시보드 업데이트 실패: {e}")
    
    async def send_performance_report(self):
        """성과 리포트 전송"""
        try:
            portfolio_value = self.paper_trading.get_total_value()
            performance = self.paper_trading.get_performance_summary()
            
            message = f"""📊 페이퍼 트레이딩 성과 리포트
            
💰 포트폴리오: ${portfolio_value:.2f}
📈 총 수익률: {((portfolio_value - self.paper_trading.initial_balance) / self.paper_trading.initial_balance) * 100:+.2f}%
📊 거래 횟수: {self.paper_trading.stats['total_trades']}회
🎯 승률: {(self.paper_trading.stats['winning_trades'] / max(1, self.paper_trading.stats['total_trades'])) * 100:.1f}%
💸 총 수수료: ${self.paper_trading.stats['total_fees_paid']:.2f}
📉 최대 손실: {self.paper_trading.stats['max_drawdown'] * 100:.1f}%

🔍 스캔 정보:
- 총 스캔: {self.performance_data['scan_cycles']}회
- 신호 발견: {self.performance_data['total_signals']}개
- 실행 거래: {self.performance_data['executed_trades']}회

⏰ 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

            self.safe_send_telegram(message)
            logger.info("📈 성과 리포트 전송 완료")
            
        except Exception as e:
            logger.error(f"❌ 성과 리포트 전송 실패: {e}")
    
    async def run_trading_cycle(self):
        """한 번의 트레이딩 사이클 실행"""
        try:
            cycle_start = datetime.now()
            logger.info("🔄 트레이딩 사이클 시작")
            
            # 1. 시장 스캔
            predictions = await self.scan_market()
            
            # 2. 페이퍼 트레이딩 실행
            await self.execute_paper_trade(predictions)
            
            # 3. 포지션 관리
            await self.manage_paper_positions()
            
            # 4. 대시보드 업데이트
            await self.update_dashboard()
            
            cycle_duration = (datetime.now() - cycle_start).total_seconds()
            logger.info(f"✅ 트레이딩 사이클 완료 (소요시간: {cycle_duration:.1f}초)")
            
        except Exception as e:
            logger.error(f"❌ 트레이딩 사이클 오류: {e}")
            traceback.print_exc()
            self.notifier.send_error_alert("TRADING_CYCLE", str(e))
    
    async def run(self):
        """메인 실행 루프"""
        try:
            if not await self.initialize():
                return
            
            # 정기 작업 카운터
            cycle_count = 0
            last_report_time = datetime.now()
            last_model_update = datetime.now()
            
            logger.info("🚀 24시간 페이퍼 트레이딩 봇 시작!")
            
            while self.is_running:
                try:
                    # 트레이딩 사이클 실행
                    await self.run_trading_cycle()
                    cycle_count += 1
                    
                    # 1시간마다 성과 리포트
                    if (datetime.now() - last_report_time).total_seconds() >= 3600:
                        await self.send_performance_report()
                        last_report_time = datetime.now()
                    
                    # 24시간마다 모델 재훈련
                    if (datetime.now() - last_model_update).total_seconds() >= 86400:
                        await self.train_models()
                        last_model_update = datetime.now()
                    
                    # 다음 사이클까지 대기 (단타용 2분)
                    logger.info(f"😴 다음 스캔까지 2분 대기... (사이클: {cycle_count})")
                    await asyncio.sleep(120)  # 2분 대기 (단타용)
                    
                except KeyboardInterrupt:
                    logger.info("👋 사용자 중단 요청")
                    break
                except Exception as e:
                    logger.error(f"❌ 메인 루프 오류: {e}")
                    traceback.print_exc()
                    await asyncio.sleep(60)  # 오류 시 1분 대기
            
        except Exception as e:
            logger.error(f"❌ 봇 실행 실패: {e}")
            traceback.print_exc()
        finally:
            # 종료 처리
            await self.shutdown()
    
    async def shutdown(self):
        """봇 종료 처리"""
        try:
            logger.info("🛑 페이퍼 트레이딩 봇 종료 중...")
            
            self.is_running = False
            
            # 최종 상태 저장
            self.paper_trading.save_state()
            self.strategy.save_positions()
            
            # 최종 성과 리포트
            await self.send_performance_report()
            
            # 종료 알림
            self.safe_send_telegram("🛑 페이퍼 트레이딩 봇이 종료되었습니다.")
            
            logger.info("✅ 페이퍼 트레이딩 봇 종료 완료")
            
        except Exception as e:
            logger.error(f"❌ 종료 처리 실패: {e}")

async def main():
    """메인 함수"""
    bot = PaperTradingBot()
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 페이퍼 트레이딩 봇 중단됨")
    except Exception as e:
        print(f"❌ 실행 오류: {e}")
