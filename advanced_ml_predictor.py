#!/usr/bin/env python3
"""
고급 ML 예측기 - 새로 훈련된 대용량 데이터셋 모델 사용
"""

import pandas as pd
import numpy as np
import joblib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger

from config import load_config
from features import FeatureEngineering
from binance_api import BinanceConnector
from utils import ensure_dir

class AdvancedMLPredictor:
    """고급 ML 예측기"""
    
    def __init__(self, config=None):
        self.config = config or load_config()
        self.feature_eng = FeatureEngineering()
        self.models_dir = Path("models")
        
        # 로드된 모델 정보
        self.model = None
        self.scaler = None
        self.feature_columns = []
        self.model_info = {}
        
        # 모델 자동 로드
        self.load_latest_model()
    
    def load_latest_model(self) -> bool:
        """가장 최신 모델 로드"""
        try:
            if not self.models_dir.exists():
                logger.warning("❌ models 디렉토리가 없습니다")
                return False
            
            # 새로 훈련된 모델 우선 확인
            new_summary_file = self.models_dir / "training_summary_new.json"
            if new_summary_file.exists():
                logger.info("🚀 새로운 고급 모델 로드 중...")
                
                with open(new_summary_file, 'r') as f:
                    summary = json.load(f)
                
                best_model = summary['best_model']
                best_auc = summary['best_auc']
                model_file = summary['results'][best_model]['model_file']
                
                # 모델 파일 로드
                model_path = self.models_dir / model_file
                if model_path.exists():
                    self.model = joblib.load(model_path)
                    
                    self.model_info = {
                        'model_name': best_model,
                        'auc_score': best_auc,
                        'dataset_size': summary['dataset_size'],
                        'feature_count': summary['feature_count']
                    }
                    
                    self.feature_columns = summary['feature_columns']
                    
                    logger.success(f"✅ 새 모델 로드: {best_model} (AUC: {best_auc:.3f})")
                    return True
            
            # 기존 모델 확인
            summary_file = self.models_dir / "training_summary.json"
            if summary_file.exists():
                logger.info("🔄 기존 모델 로드 중...")
                
                with open(summary_file, 'r') as f:
                    summary = json.load(f)
                
                # 최고 성능 모델 찾기
                best_model = None
                best_auc = 0
                
                if 'results' in summary:
                    for model_name, info in summary['results'].items():
                        if isinstance(info, dict) and 'auc_score' in info:
                            auc = info['auc_score']
                            if auc > best_auc:
                                best_auc = auc
                                best_model = model_name
                
                if best_model:
                    model_file = self.models_dir / f"{best_model}_model.pkl"
                    if model_file.exists():
                        self.model = joblib.load(model_file)
                        self.model_info = {
                            'model_name': best_model,
                            'auc_score': best_auc,
                            'legacy': True
                        }
                        
                        if 'feature_columns' in summary:
                            self.feature_columns = summary['feature_columns']
                        else:
                            # 기본 특성 설정
                            self.feature_columns = [
                                'rsi', 'macd', 'bb_position', 'atr_pct', 
                                'volume_ratio', 'price_change_1', 'sma_20', 'ema_20'
                            ]
                        
                        logger.success(f"✅ 기존 모델 로드: {best_model} (AUC: {best_auc:.3f})")
                        return True
            
            logger.warning("❌ 사용 가능한 모델이 없습니다")
            return False
            
        except Exception as e:
            logger.error(f"❌ 모델 로드 실패: {e}")
            return False
    
    def predict_symbol(self, binance: BinanceConnector, symbol: str, 
                      timeframe: str = '1h', limit: int = 200) -> Optional[Dict]:
        """심볼에 대한 급등 예측"""
        try:
            if not self.model:
                logger.error("❌ 모델이 로드되지 않았습니다")
                return None
            
            # 데이터 수집
            ohlcv_data = binance.fetch_ohlcv(symbol, timeframe, limit)
            if ohlcv_data is None or ohlcv_data.empty or len(ohlcv_data) < 50:
                return None
            
            # 특성 생성
            features_df = self.feature_eng.create_features(ohlcv_data)
            if features_df is None or features_df.empty or len(features_df) < 10:
                return None
            
            # 특성 준비
            missing_features = set(self.feature_columns) - set(features_df.columns)
            if missing_features:
                for feature in missing_features:
                    features_df[feature] = 0.0
            
            # 최신 데이터 포인트 사용
            feature_data = features_df[self.feature_columns].iloc[-1:].fillna(0.0)
            feature_data = feature_data.replace([np.inf, -np.inf], 0.0)
            X = feature_data.values
            
            # 예측
            try:
                if hasattr(self.model, 'predict_proba'):
                    prediction_proba = self.model.predict_proba(X)[0]
                    surge_probability = float(prediction_proba[1])
                else:
                    decision = self.model.decision_function(X)[0]
                    surge_probability = 1 / (1 + np.exp(-decision))
            except:
                surge_probability = 0.5
            
            # 현재 가격
            current_price = float(features_df['close'].iloc[-1])
            
            # 신뢰도 계산
            confidence = abs(surge_probability - 0.5) * 2
            
            # 신호 생성
            threshold = getattr(self.config, 'ML_PROB_THRESHOLD', 0.7)
            signal = surge_probability >= threshold
            
            result = {
                'symbol': symbol,
                'current_price': current_price,
                'surge_probability': surge_probability,
                'confidence': confidence,
                'signal': signal,
                'model_name': self.model_info.get('model_name', 'unknown'),
                'model_auc': self.model_info.get('auc_score', 0.0),
                'timestamp': datetime.now().isoformat(),
                'ensemble_probability': surge_probability  # main.py 호환성
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ {symbol} 예측 실패: {e}")
            return None
    
    # main.py 호환성을 위한 메서드들
    def load_models(self) -> bool:
        """모델 로드 상태 반환"""
        return self.model is not None
    
    def collect_training_data(self, binance, symbols, days_back=30):
        """훈련 데이터 수집 (호환용)"""
        logger.info("🔄 미리 훈련된 모델을 사용합니다")
        return pd.DataFrame()
    
    def train_models(self, df):
        """모델 훈련 (호환용)"""
        logger.info("🔄 미리 훈련된 모델을 사용합니다")
        if self.model:
            model_name = self.model_info.get('model_name', 'advanced_model')
            auc_score = self.model_info.get('auc_score', 0.8)
            return {model_name: {'auc_score': auc_score}}
        return {}
    
    def save_scalers(self):
        """스케일러 저장 (호환용)"""
        pass

def main():
    """테스트 함수"""
    print("🧪 고급 ML 예측기 테스트")
    
    try:
        config = load_config()
        predictor = AdvancedMLPredictor(config)
        
        if predictor.model:
            model_name = predictor.model_info.get('model_name', 'Unknown')
            auc_score = predictor.model_info.get('auc_score', 0)
            feature_count = len(predictor.feature_columns)
            
            print(f"✅ 모델 준비 완료!")
            print(f"  모델: {model_name}")
            print(f"  AUC: {auc_score:.3f}")
            print(f"  특성: {feature_count}개")
        else:
            print("❌ 모델 로드 실패")
            
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")

if __name__ == "__main__":
    main()
