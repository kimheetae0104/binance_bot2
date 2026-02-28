#!/usr/bin/env python3
"""
대시보드 테스트 데이터 생성기
아름다운 차트와 그래프를 위한 샘플 데이터 생성
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import random
from utils import ensure_dir, save_json

class DashboardTestDataGenerator:
    """대시보드 테스트 데이터 생성기"""
    
    def __init__(self):
        self.data_dir = ensure_dir("dashboard_data")
        
    def generate_sample_data(self):
        """완전한 샘플 데이터 생성"""
        print("🎨 대시보드 테스트 데이터 생성 중...")
        
        # 1. 성과 데이터 생성
        self.generate_performance_data()
        
        # 2. ML 통계 데이터 생성
        self.generate_ml_stats()
        
        # 3. 일일 통계 데이터 생성
        self.generate_daily_stats()
        
        print("✅ 테스트 데이터 생성 완료!")
        print("🚀 이제 대시보드를 실행해보세요: ./run_dashboard.sh")
    
    def generate_performance_data(self):
        """성과 데이터 생성"""
        # 시작 잔고
        initial_balance = 77.0
        current_balance = initial_balance
        
        # 잔고 히스토리 생성 (지난 30일)
        balance_history = []
        trades = []
        
        base_time = datetime.now() - timedelta(days=30)
        
        winning_trades = 0
        losing_trades = 0
        total_profit = 0.0
        
        # 매일 2-8개의 거래 생성
        for day in range(30):
            day_time = base_time + timedelta(days=day)
            
            # 하루 거래 수 (랜덤)
            daily_trades = random.randint(2, 8)
            daily_pnl = 0
            
            for trade_idx in range(daily_trades):
                trade_time = day_time + timedelta(
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
                
                # 거래 생성
                symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT', 
                          'DOTUSDT', 'LINKUSDT', 'AVAXUSDT', 'MATICUSDT', 'ALGOUSDT']
                symbol = random.choice(symbols)
                
                side = random.choice(['buy', 'sell'])
                amount = random.uniform(0.001, 0.1)
                price = random.uniform(10, 50000)
                
                # 수익/손실 계산 (전체적으로 약간의 수익이 나도록 조정)
                profit_probability = 0.58  # 58% 승률
                if random.random() < profit_probability:
                    profit = random.uniform(0.5, 15.0)
                    winning_trades += 1
                else:
                    profit = -random.uniform(0.3, 8.0)
                    losing_trades += 1
                
                total_profit += profit
                daily_pnl += profit
                current_balance += profit
                
                # 거래 기록 추가
                trade = {
                    'symbol': symbol,
                    'side': side,
                    'amount': amount,
                    'price': price,
                    'profit': profit,
                    'timestamp': trade_time.isoformat()
                }
                trades.append(trade)
            
            # 일일 잔고 기록
            balance_history.append({
                'timestamp': day_time.isoformat(),
                'balance': current_balance,
                'daily_pnl': daily_pnl
            })
        
        # 성과 데이터 구성
        total_trades = len(trades)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # 최대 드로우다운 계산
        peak = initial_balance
        max_drawdown = 0
        for record in balance_history:
            balance = record['balance']
            if balance > peak:
                peak = balance
            drawdown = (peak - balance) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # 샤프 비율 계산 (단순화)
        if len(balance_history) > 1:
            daily_returns = []
            for i in range(1, len(balance_history)):
                prev_balance = balance_history[i-1]['balance']
                curr_balance = balance_history[i]['balance']
                if prev_balance > 0:
                    daily_return = (curr_balance - prev_balance) / prev_balance
                    daily_returns.append(daily_return)
            
            if daily_returns:
                mean_return = np.mean(daily_returns)
                std_return = np.std(daily_returns)
                sharpe_ratio = mean_return / std_return if std_return > 0 else 0
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0
        
        performance_data = {
            'trades': trades,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'total_profit': total_profit,
            'win_rate': win_rate,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'balance_history': balance_history
        }
        
        # 파일 저장
        save_json(performance_data, str(self.data_dir / "performance.json"))
        print(f"📊 성과 데이터 생성: {total_trades}건 거래, {win_rate*100:.1f}% 승률")
    
    def generate_ml_stats(self):
        """ML 통계 데이터 생성"""
        # 특성 중요도 (실제 특성명들)
        features = [
            'rsi_14', 'macd_signal', 'bb_upper_ratio', 'volume_sma_ratio',
            'price_change_1h', 'volatility_7d', 'momentum_5', 'support_distance',
            'resistance_breakout', 'volume_trend', 'ma_convergence', 'stoch_k',
            'williams_r', 'atr_ratio', 'price_acceleration', 'volume_price_corr'
        ]
        
        feature_importance = []
        for feature in features:
            importance = random.uniform(0.01, 0.15)
            feature_importance.append({
                'feature': feature,
                'importance': importance
            })
        
        # 예측 히스토리 생성
        prediction_history = []
        base_time = datetime.now() - timedelta(days=7)
        
        for hour in range(7 * 24):  # 지난 7일, 시간별
            pred_time = base_time + timedelta(hours=hour)
            
            # 예측 정확도는 시간에 따라 변화
            base_accuracy = 0.65
            noise = random.uniform(-0.1, 0.1)
            accuracy = max(0.4, min(0.9, base_accuracy + noise))
            
            confidence = random.uniform(0.5, 0.95)
            
            prediction_history.append({
                'timestamp': pred_time.isoformat(),
                'accuracy': accuracy,
                'confidence': confidence,
                'prediction': random.choice([0, 1]),
                'actual': random.choice([0, 1])
            })
        
        ml_stats = {
            'model_accuracy': 0.68,
            'model_precision': 0.72,
            'model_recall': 0.65,
            'model_f1': 0.68,
            'prediction_history': prediction_history,
            'feature_importance': feature_importance,
            'model_training_date': (datetime.now() - timedelta(days=3)).isoformat(),
            'total_predictions': len(prediction_history),
            'correct_predictions': int(len(prediction_history) * 0.68)
        }
        
        # 파일 저장
        save_json(ml_stats, str(self.data_dir / "ml_performance.json"))
        print(f"🤖 ML 통계 생성: {len(feature_importance)}개 특성, {len(prediction_history)}건 예측")
    
    def generate_daily_stats(self):
        """일일 통계 데이터 생성"""
        # 일일 수익 (지난 30일)
        daily_profits = []
        daily_trades = []
        
        for day in range(30):
            date = (datetime.now() - timedelta(days=29-day)).strftime('%Y-%m-%d')
            
            # 일일 수익
            daily_profit = random.uniform(-20, 50)  # 평균적으로 수익
            daily_profits.append({
                'date': date,
                'profit': daily_profit,
                'profit_percent': daily_profit / 77.0 * 100  # 초기 자본 대비
            })
            
            # 일일 거래 수
            num_trades = random.randint(2, 8)
            daily_trades.append({
                'date': date,
                'count': num_trades,
                'win_count': random.randint(1, num_trades),
                'loss_count': num_trades - random.randint(1, num_trades)
            })
        
        # 월별 요약
        monthly_summary = {
            'total_profit': sum(d['profit'] for d in daily_profits),
            'total_trades': sum(d['count'] for d in daily_trades),
            'avg_daily_profit': np.mean([d['profit'] for d in daily_profits]),
            'best_day': max(daily_profits, key=lambda x: x['profit']),
            'worst_day': min(daily_profits, key=lambda x: x['profit']),
            'profitable_days': len([d for d in daily_profits if d['profit'] > 0])
        }
        
        # 주별 요약
        weekly_summary = {
            'week1_profit': sum(d['profit'] for d in daily_profits[:7]),
            'week2_profit': sum(d['profit'] for d in daily_profits[7:14]),
            'week3_profit': sum(d['profit'] for d in daily_profits[14:21]),
            'week4_profit': sum(d['profit'] for d in daily_profits[21:28])
        }
        
        daily_stats = {
            'daily_profits': daily_profits,
            'daily_trades': daily_trades,
            'monthly_summary': monthly_summary,
            'weekly_summary': weekly_summary,
            'generated_at': datetime.now().isoformat()
        }
        
        # 파일 저장
        save_json(daily_stats, str(self.data_dir / "daily_stats.json"))
        print(f"📅 일일 통계 생성: 30일 데이터, 총 {monthly_summary['total_profit']:.2f}$ 수익")

if __name__ == "__main__":
    generator = DashboardTestDataGenerator()
    generator.generate_sample_data()
