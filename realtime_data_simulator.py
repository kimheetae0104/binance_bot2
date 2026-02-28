#!/usr/bin/env python3
"""
대시보드 실시간 데이터 업데이트 시뮬레이터
실시간 거래와 ML 성능 데이터를 시뮬레이션합니다.
"""

import asyncio
import random
import json
from datetime import datetime, timedelta
from pathlib import Path
import time
from utils import load_json, save_json, ensure_dir
from loguru import logger

class RealTimeDataSimulator:
    """실시간 데이터 시뮬레이터"""
    
    def __init__(self):
        self.data_dir = ensure_dir("dashboard_data")
        self.performance_file = self.data_dir / "performance.json"
        self.ml_stats_file = self.data_dir / "ml_performance.json"
        self.running = True
        
    async def simulate_real_time_updates(self):
        """실시간 업데이트 시뮬레이션"""
        logger.info("🔄 실시간 데이터 업데이트 시작...")
        
        while self.running:
            try:
                # 새로운 거래 시뮬레이션 (30% 확률)
                if random.random() < 0.3:
                    await self.add_new_trade()
                
                # 잔고 업데이트 (매번)
                await self.update_balance()
                
                # ML 예측 업데이트 (20% 확률)
                if random.random() < 0.2:
                    await self.add_ml_prediction()
                
                # 5초 대기
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"실시간 업데이트 오류: {e}")
                await asyncio.sleep(5)
    
    async def add_new_trade(self):
        """새로운 거래 추가"""
        try:
            # 기존 데이터 로드
            performance_data = load_json(str(self.performance_file), {})
            
            # 새로운 거래 생성
            symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
            new_trade = {
                'symbol': random.choice(symbols),
                'side': random.choice(['buy', 'sell']),
                'amount': round(random.uniform(0.001, 0.1), 6),
                'price': round(random.uniform(10, 50000), 4),
                'profit': round(random.uniform(-5, 10), 4),  # 약간 양의 편향
                'timestamp': datetime.now().isoformat()
            }
            
            # 거래 목록에 추가
            if 'trades' not in performance_data:
                performance_data['trades'] = []
            
            performance_data['trades'].append(new_trade)
            
            # 통계 업데이트
            self.update_performance_stats(performance_data)
            
            # 저장
            save_json(performance_data, str(self.performance_file))
            
            logger.info(f"💰 새 거래: {new_trade['symbol']} ${new_trade['profit']:+.2f}")
            
        except Exception as e:
            logger.error(f"거래 추가 오류: {e}")
    
    async def update_balance(self):
        """잔고 업데이트"""
        try:
            performance_data = load_json(str(self.performance_file), {})
            
            # 현재 잔고 계산
            initial_balance = 77.0
            total_profit = sum(trade.get('profit', 0) for trade in performance_data.get('trades', []))
            current_balance = initial_balance + total_profit
            
            # 잔고 히스토리 업데이트
            if 'balance_history' not in performance_data:
                performance_data['balance_history'] = []
            
            # 최근 기록이 5분 이상 오래되었으면 새 기록 추가
            now = datetime.now()
            if (not performance_data['balance_history'] or 
                (now - datetime.fromisoformat(performance_data['balance_history'][-1]['timestamp'])).total_seconds() > 300):
                
                performance_data['balance_history'].append({
                    'timestamp': now.isoformat(),
                    'balance': current_balance
                })
                
                # 히스토리가 너무 길면 오래된 것 제거 (최대 1000개)
                if len(performance_data['balance_history']) > 1000:
                    performance_data['balance_history'] = performance_data['balance_history'][-1000:]
                
                save_json(performance_data, str(self.performance_file))
                
        except Exception as e:
            logger.error(f"잔고 업데이트 오류: {e}")
    
    async def add_ml_prediction(self):
        """ML 예측 추가"""
        try:
            ml_stats = load_json(str(self.ml_stats_file), {})
            
            # 새로운 예측 생성
            prediction = {
                'timestamp': datetime.now().isoformat(),
                'prediction': random.choice([0, 1]),
                'confidence': round(random.uniform(0.5, 0.95), 3),
                'accuracy': round(random.uniform(0.55, 0.85), 3)
            }
            
            # 예측 히스토리에 추가
            if 'prediction_history' not in ml_stats:
                ml_stats['prediction_history'] = []
            
            ml_stats['prediction_history'].append(prediction)
            
            # 히스토리가 너무 길면 제거 (최대 500개)
            if len(ml_stats['prediction_history']) > 500:
                ml_stats['prediction_history'] = ml_stats['prediction_history'][-500:]
            
            # ML 통계 업데이트
            recent_predictions = ml_stats['prediction_history'][-50:]  # 최근 50개
            if recent_predictions:
                avg_accuracy = sum(p['accuracy'] for p in recent_predictions) / len(recent_predictions)
                ml_stats['model_accuracy'] = avg_accuracy
            
            save_json(ml_stats, str(self.ml_stats_file))
            
            logger.info(f"🤖 ML 예측: {prediction['confidence']:.1%} 신뢰도")
            
        except Exception as e:
            logger.error(f"ML 예측 오류: {e}")
    
    def update_performance_stats(self, performance_data):
        """성과 통계 업데이트"""
        trades = performance_data.get('trades', [])
        
        if not trades:
            return
        
        # 기본 통계
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.get('profit', 0) > 0])
        losing_trades = total_trades - winning_trades
        total_profit = sum(t.get('profit', 0) for t in trades)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # 업데이트
        performance_data.update({
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'total_profit': total_profit,
            'win_rate': win_rate
        })
    
    def stop(self):
        """시뮬레이터 정지"""
        self.running = False
        logger.info("🛑 실시간 데이터 시뮬레이터 정지")

async def main():
    """메인 실행"""
    simulator = RealTimeDataSimulator()
    
    try:
        await simulator.simulate_real_time_updates()
    except KeyboardInterrupt:
        simulator.stop()
        logger.info("✅ 시뮬레이터가 정상적으로 종료되었습니다.")

if __name__ == "__main__":
    logger.info("🚀 실시간 데이터 시뮬레이터 시작")
    logger.info("Ctrl+C로 종료할 수 있습니다.")
    
    asyncio.run(main())
