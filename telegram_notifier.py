"""
텔레그램 알림 서비스
"""

import requests
import asyncio
import json
from typing import Optional, Dict, Any
from loguru import logger
from datetime import datetime

class TelegramNotifier:
    """텔레그램 알림 봇"""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        
        if bot_token and chat_id:
            self.enabled = True
            logger.info("✅ 텔레그램 알림 활성화")
        else:
            self.enabled = False
            logger.warning("⚠️ 텔레그램 설정이 없습니다")
    
    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """메시지 전송 (재시도 로직 포함)"""
        if not self.enabled:
            return False
        
        # 메시지 길이 제한 (텔레그램 한계: 4096자)
        if len(message) > 4000:
            message = message[:3900] + "\n\n... (메시지 길이로 인한 생략)"
        
        max_retries = 3
        timeouts = [15, 20, 30]  # 점진적 타임아웃 증가
        
        for attempt in range(max_retries):
            try:
                url = f"{self.base_url}/sendMessage"
                payload = {
                    'chat_id': self.chat_id,
                    'text': message,
                    'parse_mode': parse_mode
                }
                
                timeout = timeouts[attempt]
                logger.debug(f"📨 텔레그램 전송 시도 {attempt+1}/{max_retries} (타임아웃: {timeout}초)")
                
                response = requests.post(url, json=payload, timeout=timeout)
                
                if response.status_code == 200:
                    logger.debug("✅ 텔레그램 메시지 전송 성공")
                    return True
                elif response.status_code == 429:
                    # Rate limit 오류
                    logger.warning("⚠️ 텔레그램 API 한계 도달, 잠시 대기...")
                    import time
                    time.sleep(5)
                    continue
                else:
                    logger.warning(f"⚠️ 텔레그램 전송 실패 (시도 {attempt+1}): {response.status_code}")
                    if attempt == max_retries - 1:
                        logger.error(f"❌ 텔레그램 전송 최종 실패: {response.status_code}")
                        return False
                    continue
                    
            except requests.exceptions.ReadTimeout:
                logger.warning(f"⏰ 텔레그램 읽기 타임아웃 (시도 {attempt+1}/{max_retries})")
                if attempt == max_retries - 1:
                    logger.error("❌ 텔레그램 전송 최종 실패: 타임아웃")
                    return False
                continue
            except requests.exceptions.ConnectionError:
                logger.warning(f"🌐 텔레그램 연결 오류 (시도 {attempt+1}/{max_retries})")
                if attempt == max_retries - 1:
                    logger.error("❌ 텔레그램 전송 최종 실패: 연결 오류")
                    return False
                continue
            except Exception as e:
                logger.warning(f"⚠️ 텔레그램 전송 오류 (시도 {attempt+1}): {e}")
                if attempt == max_retries - 1:
                    logger.error(f"❌ 텔레그램 전송 최종 실패: {e}")
                    return False
                continue
        
        return False
    
    async def send_message_async(self, message: str, parse_mode: str = "HTML") -> bool:
        """비동기 메시지 전송 (백그라운드 실행용)"""
        if not self.enabled:
            return False
        
        # 메시지 길이 제한
        if len(message) > 4000:
            message = message[:3900] + "\n\n... (메시지 길이로 인한 생략)"
        
        max_retries = 2  # 비동기에서는 더 적은 재시도
        
        for attempt in range(max_retries):
            try:
                import aiohttp
                
                url = f"{self.base_url}/sendMessage"
                payload = {
                    'chat_id': self.chat_id,
                    'text': message,
                    'parse_mode': parse_mode
                }
                
                timeout = aiohttp.ClientTimeout(total=20)
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(url, json=payload) as response:
                        if response.status == 200:
                            logger.debug("✅ 텔레그램 비동기 전송 성공")
                            return True
                        else:
                            logger.warning(f"⚠️ 텔레그램 비동기 전송 실패: {response.status}")
                            
            except asyncio.TimeoutError:
                logger.warning(f"⏰ 텔레그램 비동기 타임아웃 (시도 {attempt+1})")
            except Exception as e:
                logger.warning(f"⚠️ 텔레그램 비동기 오류: {e}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(2)  # 재시도 전 대기
        
        logger.error("❌ 텔레그램 비동기 전송 최종 실패")
        return False
    
    def send_message_safe(self, message: str, parse_mode: str = "HTML") -> bool:
        """안전한 메시지 전송 (오류 시 무시)"""
        try:
            return self.send_message(message, parse_mode)
        except Exception as e:
            logger.warning(f"⚠️ 텔레그램 안전 전송 실패 (무시됨): {e}")
            return False
    
    def send_trade_entry(self, symbol: str, price: float, quantity: float, 
                        probability: float, confidence: str, amount: float):
        """진입 알림"""
        message = (
            f"🚀 <b>매수 진입</b>\n\n"
            f"📈 심볼: <code>{symbol}</code>\n"
            f"💰 가격: <code>${price:.6f}</code>\n"
            f"📊 수량: <code>{quantity:.2f}</code>\n"
            f"💵 금액: <code>${amount:.2f}</code>\n"
            f"🎯 확률: <code>{probability:.1%}</code>\n"
            f"⭐ 신뢰도: <code>{confidence}</code>\n"
            f"⏰ 시간: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>"
        )
        return self.send_message(message)
    
    def send_trade_exit(self, symbol: str, entry_price: float, exit_price: float,
                       quantity: float, pnl_pct: float, pnl_amount: float, 
                       reason: str, duration_hours: float):
        """청산 알림"""
        profit_emoji = "🟢" if pnl_amount > 0 else "🔴"
        
        message = (
            f"{profit_emoji} <b>포지션 청산</b>\n\n"
            f"📈 심볼: <code>{symbol}</code>\n"
            f"📍 진입가: <code>${entry_price:.6f}</code>\n"
            f"📍 청산가: <code>${exit_price:.6f}</code>\n"
            f"📊 수량: <code>{quantity:.2f}</code>\n"
            f"💰 수익률: <code>{pnl_pct:+.2f}%</code>\n"
            f"💵 손익: <code>${pnl_amount:+.2f}</code>\n"
            f"🏷️ 사유: <code>{reason}</code>\n"
            f"⏱️ 보유시간: <code>{duration_hours:.1f}시간</code>\n"
            f"⏰ 시간: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>"
        )
        return self.send_message(message)
    
    def send_signal_alert(self, symbol: str, probability: float, confidence: str, 
                         current_price: float, action: str):
        """신호 알림"""
        emoji = "🚀" if action == "buy" else "⏸️"
        
        message = (
            f"{emoji} <b>거래 신호</b>\n\n"
            f"📈 심볼: <code>{symbol}</code>\n"
            f"📊 액션: <code>{action.upper()}</code>\n"
            f"🎯 확률: <code>{probability:.1%}</code>\n"
            f"⭐ 신뢰도: <code>{confidence}</code>\n"
            f"💰 현재가: <code>${current_price:.6f}</code>\n"
            f"⏰ 시간: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>"
        )
        return self.send_message(message)
    
    def send_portfolio_summary(self, summary: Dict[str, Any]):
        """포트폴리오 요약"""
        stats = summary.get('performance_stats', {})
        
        message = (
            f"📊 <b>포트폴리오 요약</b>\n\n"
            f"🏛️ 보유 포지션: <code>{summary['total_positions']}개</code>\n"
            f"💰 총 가치: <code>${summary['total_value']:.2f}</code>\n"
            f"📈 미실현 손익: <code>${summary['total_unrealized_pnl']:+.2f}</code>\n\n"
            f"📋 <b>거래 통계</b>\n"
            f"🎯 총 거래: <code>{stats.get('total_trades', 0)}회</code>\n"
            f"✅ 수익 거래: <code>{stats.get('winning_trades', 0)}회</code>\n"
            f"❌ 손실 거래: <code>{stats.get('losing_trades', 0)}회</code>\n"
            f"📊 승률: <code>{stats.get('win_rate', 0):.1%}</code>\n"
            f"💵 총 손익: <code>${stats.get('total_pnl', 0):+.2f}</code>\n"
            f"⏰ 시간: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>"
        )
        
        # 개별 포지션 정보 추가
        if summary['positions']:
            message += f"\n\n🏦 <b>개별 포지션</b>\n"
            for pos in summary['positions'][:5]:  # 최대 5개만 표시
                message += (
                    f"• <code>{pos['symbol']}</code>: "
                    f"${pos['current_price']:.6f} "
                    f"({pos['unrealized_pnl_pct']:+.1f}%)\n"
                )
        
        return self.send_message(message)
    
    def send_error_alert(self, error_type: str, error_message: str, symbol: str = ""):
        """오류 알림"""
        message = (
            f"⚠️ <b>시스템 오류</b>\n\n"
            f"🏷️ 유형: <code>{error_type}</code>\n"
            f"📈 심볼: <code>{symbol if symbol else 'N/A'}</code>\n"
            f"📝 메시지: <code>{error_message[:200]}</code>\n"
            f"⏰ 시간: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>"
        )
        return self.send_message(message)
    
    def send_startup_message(self, config: Dict[str, Any]):
        """봇 시작 알림"""
        message = (
            f"🤖 <b>ML 트레이딩 봇 시작</b>\n\n"
            f"📊 모드: <code>{config.get('TRADE_MODE', 'unknown')}</code>\n"
            f"🏦 테스트넷: <code>{'예' if config.get('USE_TESTNET', True) else '아니오'}</code>\n"
            f"💰 초기 자본: <code>${config.get('INITIAL_BALANCE', 0):.2f}</code>\n"
            f"🎯 ML 임계값: <code>{config.get('ML_PROB_THRESHOLD', 0.65):.1%}</code>\n"
            f"🛡️ 손절선: <code>{config.get('STOP_LOSS_PCT', 0.03):.1%}</code>\n"
            f"💎 익절선: <code>{config.get('TAKE_PROFIT_PCT', 0.05):.1%}</code>\n"
            f"⏰ 시작: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>"
        )
        return self.send_message(message)
    
    def send_daily_report(self, trades_today: int, pnl_today: float, 
                         win_rate_today: float, total_positions: int):
        """일일 리포트"""
        message = (
            f"📅 <b>일일 거래 리포트</b>\n\n"
            f"📊 오늘 거래: <code>{trades_today}회</code>\n"
            f"💰 오늘 손익: <code>${pnl_today:+.2f}</code>\n"
            f"🎯 오늘 승률: <code>{win_rate_today:.1%}</code>\n"
            f"🏛️ 현재 포지션: <code>{total_positions}개</code>\n"
            f"📅 날짜: <code>{datetime.now().strftime('%Y-%m-%d')}</code>"
        )
        return self.send_message(message)
    
    def send_model_update(self, model_count: int, best_model: str, auc_score: float):
        """모델 업데이트 알림"""
        message = (
            f"🧠 <b>ML 모델 업데이트</b>\n\n"
            f"🔧 훈련된 모델: <code>{model_count}개</code>\n"
            f"🏆 최고 모델: <code>{best_model}</code>\n"
            f"📊 AUC 스코어: <code>{auc_score:.3f}</code>\n"
            f"⏰ 업데이트: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>"
        )
        return self.send_message(message)
