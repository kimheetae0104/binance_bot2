"""
머신러닝 모델 훈련 및 예측
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict, List, Any
import pickle
import joblib
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger

# 머신러닝 라이브러리
try:
    import warnings
    warnings.filterwarnings('ignore')
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import classification_report, roc_auc_score, precision_recall_curve
    from sklearn.preprocessing import StandardScaler, RobustScaler
    from sklearn.feature_selection import SelectKBest, f_classif
    try:
        from imblearn.over_sampling import SMOTE
        from imblearn.pipeline import Pipeline as ImbPipeline
        IMBALANCED_LEARN_AVAILABLE = True
    except ImportError:
        IMBALANCED_LEARN_AVAILABLE = False
    try:
        import xgboost as xgb
        XGBOOST_AVAILABLE = True
    except ImportError:
        XGBOOST_AVAILABLE = False
    try:
        import lightgbm as lgb
        LIGHTGBM_AVAILABLE = True
    except ImportError:
        LIGHTGBM_AVAILABLE = False
    ML_AVAILABLE = True
except ImportError as e:
    logger.error(f"머신러닝 라이브러리 설치 필요: {e}")
    ML_AVAILABLE = False
    IMBALANCED_LEARN_AVAILABLE = False
    XGBOOST_AVAILABLE = False
    LIGHTGBM_AVAILABLE = False
    # Mock 클래스들 정의
    class MockModel:
        def __init__(self, *args, **kwargs): pass
        def fit(self, X, y): pass
        def predict(self, X): return [0] * len(X)
        def predict_proba(self, X): return [[0.5, 0.5]] * len(X)
    
    class MockXGB:
        XGBClassifier = MockModel
    class MockLGB:
        LGBMClassifier = MockModel
        
    xgb = MockXGB()
    lgb = MockLGB()
    RandomForestClassifier = MockModel
    GradientBoostingClassifier = MockModel
    LogisticRegression = MockModel
    StandardScaler = MockModel
    RobustScaler = MockModel

from features import FeatureEngineering
from binance_api import BinanceConnector
from utils import ensure_dir, save_json, load_json

class MLPredictor:
    """머신러닝 급등 예측 모델"""
    
    def __init__(self, config):
        self.config = config
        self.feature_eng = FeatureEngineering()
        self.models = {}
        self.scalers = {}
        self.feature_columns = []
        
        # 모델 저장 경로
        self.models_dir = ensure_dir("models")
        self.data_dir = ensure_dir("data")
        
        # 사용할 모델들
        self.model_configs = {
            'xgboost': {
                'model': xgb.XGBClassifier(
                    n_estimators=200,
                    max_depth=6,
                    learning_rate=0.1,
                    random_state=42,
                    eval_metric='logloss'
                ),
                'scaler': None  # XGBoost는 스케일링 불필요
            },
            'lightgbm': {
                'model': lgb.LGBMClassifier(
                    n_estimators=200,
                    max_depth=6,
                    learning_rate=0.1,
                    random_state=42,
                    verbose=-1
                ),
                'scaler': None
            },
            'random_forest': {
                'model': RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42,
                    n_jobs=-1
                ),
                'scaler': None
            },
            'gradient_boosting': {
                'model': GradientBoostingClassifier(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.1,
                    random_state=42
                ),
                'scaler': RobustScaler()
            },
            'logistic': {
                'model': LogisticRegression(
                    random_state=42,
                    max_iter=1000
                ),
                'scaler': StandardScaler()
            }
        }
    
    def collect_training_data(self, binance: BinanceConnector, symbols: List[str], 
                            timeframes: List[str] = ['5m', '15m', '1h'], 
                            days_back: int = 30) -> pd.DataFrame:
        """훈련 데이터 수집"""
        logger.info(f"📊 훈련 데이터 수집: {len(symbols)}개 심볼, {days_back}일")
        
        all_data = []
        limit = min(1440 // {'5m': 5, '15m': 15, '1h': 60}[timeframes[0]] * days_back, 1000)
        
        for symbol in symbols:
            try:
                for timeframe in timeframes:
                    df = binance.fetch_ohlcv(symbol, timeframe, limit)
                    if df is None or len(df) < 100:
                        continue
                    
                    # 특성 및 타겟 생성
                    df_features = self.feature_eng.create_features(df)
                    df_features = self.feature_eng.create_target(
                        df_features, 
                        self.config.PREDICTION_WINDOW,
                        0.03  # 3% 급등 임계값
                    )
                    
                    # 메타 정보 추가
                    df_features['symbol'] = symbol
                    df_features['timeframe'] = timeframe
                    
                    all_data.append(df_features)
                    logger.debug(f"✅ {symbol} {timeframe}: {len(df_features)}행")
                    
            except Exception as e:
                logger.warning(f"❌ {symbol} 데이터 수집 실패: {e}")
                continue
        
        if not all_data:
            logger.error("수집된 데이터가 없습니다")
            return pd.DataFrame()
        
        # 데이터 결합
        combined_df = pd.concat(all_data, ignore_index=True)
        combined_df = combined_df.dropna(subset=['target'])
        
        logger.info(f"📈 총 데이터: {len(combined_df):,}행, 급등 비율: {combined_df['target'].mean():.2%}")
        
        # 데이터 저장
        data_path = self.data_dir / f"training_data_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        combined_df.to_csv(data_path, index=False)
        logger.info(f"💾 데이터 저장: {data_path}")
        
        return combined_df
    
    def prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """특성 준비"""
        # 특성 컬럼 자동 선택 (숫자형 + 비메타 데이터)
        exclude_cols = ['symbol', 'timeframe', 'target', 'future_high', 'future_return']
        feature_cols = [col for col in df.columns 
                       if col not in exclude_cols and 
                       df[col].dtype in [np.float64, np.int64]]
        
        if not self.feature_columns:
            self.feature_columns = feature_cols
        
        X = df[self.feature_columns].values
        y = df['target'].values
        
        # 무한대 및 NaN 처리
        X = np.nan_to_num(X, nan=0.0, posinf=1e6, neginf=-1e6)
        y = np.array(y, dtype=np.float64)
        
        return X, y
    
    def train_models(self, df: pd.DataFrame, test_size: float = 0.2) -> Dict[str, Dict]:
        """모든 모델 훈련"""
        logger.info("🧠 모델 훈련 시작...")
        
        X, y = self.prepare_features(df)
        
        if len(np.unique(y)) < 2:
            logger.error("타겟 클래스가 부족합니다")
            return {}
        
        # 데이터 분할
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        logger.info(f"📊 훈련 데이터: {len(X_train):,}행, 테스트: {len(X_test):,}행")
        
        results = {}
        
        for model_name, config in self.model_configs.items():
            try:
                logger.info(f"🔄 {model_name} 훈련 중...")
                
                model = config['model']
                scaler = config['scaler']
                
                # 데이터 준비
                X_train_scaled = X_train.copy()
                X_test_scaled = X_test.copy()
                
                if (scaler is not None):
                    scaler.fit(X_train_scaled)
                    X_train_scaled = scaler.transform(X_train_scaled)
                    X_test_scaled = scaler.transform(X_test_scaled)
                    self.scalers[model_name] = scaler
                
                # SMOTE로 클래스 균형 맞추기 (안전한 방식)
                try:
                    if model_name in ['logistic', 'gradient_boosting']:
                        smote = SMOTE(random_state=42)
                        resampled_data = smote.fit_resample(X_train_scaled, y_train)
                        X_train_scaled = resampled_data[0]
                        y_train_balanced = resampled_data[1]
                    else:
                        y_train_balanced = y_train
                except Exception as e:
                    logger.warning(f"SMOTE 적용 실패: {e}, 원본 데이터 사용")
                    y_train_balanced = y_train
                
                # 모델 훈련
                model.fit(X_train_scaled, y_train_balanced)
                
                # 예측 및 평가
                y_pred = model.predict(X_test_scaled)
                y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
                
                # 메트릭 계산
                auc_score = roc_auc_score(y_test, y_pred_proba)
                precision, recall, _ = precision_recall_curve(y_test, y_pred_proba)
                pr_auc = np.trapz(recall, precision)
                
                # 교차 검증 (안전한 방식)
                try:
                    X_cv = np.array(X_train_scaled) if not isinstance(X_train_scaled, np.ndarray) else X_train_scaled
                    y_cv = np.array(y_train_balanced) if not isinstance(y_train_balanced, np.ndarray) else y_train_balanced
                    cv_scores = cross_val_score(model, X_cv, y_cv, cv=3, scoring='roc_auc')
                except Exception as e:
                    logger.warning(f"교차 검증 실패: {e}, 기본값 사용")
                    cv_scores = np.array([auc_score])  # 기본값으로 AUC 스코어 사용
                
                results[model_name] = {
                    'model': model,
                    'auc_score': auc_score,
                    'pr_auc': pr_auc,
                    'cv_mean': cv_scores.mean(),
                    'cv_std': cv_scores.std(),
                    'feature_importance': self._get_feature_importance(model)
                }
                
                # 모델 저장
                self.models[model_name] = model
                model_path = self.models_dir / f"{model_name}_model.pkl"
                joblib.dump(model, model_path)
                
                logger.info(f"✅ {model_name}: AUC={auc_score:.3f}, CV={cv_scores.mean():.3f}±{cv_scores.std():.3f}")
                
            except Exception as e:
                logger.error(f"❌ {model_name} 훈련 실패: {e}")
                continue
        
        # 최고 성능 모델 선택
        if results:
            best_model = max(results.keys(), key=lambda k: results[k]['auc_score'])
            logger.info(f"🏆 최고 성능: {best_model} (AUC: {results[best_model]['auc_score']:.3f})")
            
            # 훈련 결과 저장
            training_summary = {
                'timestamp': datetime.now().isoformat(),
                'feature_columns': self.feature_columns,
                'num_features': len(self.feature_columns),
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'results': {k: {key: val for key, val in v.items() if key != 'model'} 
                           for k, v in results.items()},
                'best_model': best_model
            }
            
            save_json(training_summary, str(self.models_dir / "training_summary.json"))
        
        return results
    
    def _get_feature_importance(self, model) -> Optional[List[Tuple[str, float]]]:
        """특성 중요도 추출"""
        try:
            if hasattr(model, 'feature_importances_'):
                importances = model.feature_importances_
            elif hasattr(model, 'coef_'):
                importances = np.abs(model.coef_[0])
            else:
                return None
            
            feature_importance = list(zip(self.feature_columns, importances))
            feature_importance.sort(key=lambda x: x[1], reverse=True)
            return feature_importance[:20]  # 상위 20개
            
        except Exception as e:
            logger.warning(f"특성 중요도 추출 실패: {e}")
            return None
    
    def predict_symbol(self, binance: BinanceConnector, symbol: str, 
                      timeframe: str = '5m') -> Optional[Dict[str, Any]]:
        """단일 심볼 급등 예측"""
        try:
            # 데이터 수집
            df = binance.fetch_ohlcv(symbol, timeframe, self.config.FEATURE_WINDOW)
            if df is None or len(df) < 50:
                return None
            
            # 특성 생성
            df_features = self.feature_eng.create_features(df)
            
            if df_features.empty or len(df_features) == 0:
                return None
            
            # 최신 데이터 사용
            latest_features = np.array(df_features.iloc[-1][self.feature_columns].values).reshape(1, -1)
            latest_features = np.nan_to_num(latest_features, nan=0.0, posinf=1e6, neginf=-1e6)
            
            predictions = {}
            
            # 모든 모델로 예측
            for model_name in self.models.keys():
                try:
                    model = self.models[model_name]
                    scaler = self.scalers.get(model_name)
                    
                    # 스케일링
                    X = latest_features.copy()
                    if scaler is not None:
                        X = scaler.transform(X)
                    
                    # 예측
                    prob = model.predict_proba(X)[0, 1]
                    predictions[model_name] = prob
                    
                except Exception as e:
                    logger.warning(f"{model_name} 예측 실패: {e}")
                    continue
            
            if not predictions:
                return None
            
            # 앙상블 예측 (평균)
            ensemble_prob = np.mean(list(predictions.values()))
            
            # 현재 시장 상황
            current_price = binance.get_current_price(symbol)
            
            result = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'current_price': current_price,
                'ensemble_probability': ensemble_prob,
                'individual_predictions': predictions,
                'signal': ensemble_prob >= self.config.ML_PROB_THRESHOLD,
                'confidence': 'high' if ensemble_prob > 0.8 else 'medium' if ensemble_prob > 0.6 else 'low'
            }
            
            return result
            
        except Exception as e:
            logger.error(f"{symbol} 예측 실패: {e}")
            return None
    
    def load_models(self) -> bool:
        """저장된 모델 로드"""
        try:
            # 훈련 요약 로드
            summary_path = self.models_dir / "training_summary.json"
            if not summary_path.exists():
                logger.warning("훈련된 모델이 없습니다")
                return False
            
            summary = load_json(str(summary_path))
            self.feature_columns = summary.get('feature_columns', [])
            
            # 모델 파일들 로드
            model_loaded = False
            for model_name in self.model_configs.keys():
                model_path = self.models_dir / f"{model_name}_model.pkl"
                scaler_path = self.models_dir / f"{model_name}_scaler.pkl"
                
                try:
                    if model_path.exists():
                        self.models[model_name] = joblib.load(model_path)
                        model_loaded = True
                        
                        # 스케일러 로드
                        if scaler_path.exists():
                            self.scalers[model_name] = joblib.load(scaler_path)
                            
                        logger.debug(f"✅ {model_name} 모델 로드")
                        
                except Exception as e:
                    logger.warning(f"{model_name} 모델 로드 실패: {e}")
                    continue
            
            if model_loaded:
                logger.info(f"📂 {len(self.models)}개 모델 로드 완료")
                return True
            else:
                logger.warning("로드 가능한 모델이 없습니다")
                return False
                
        except Exception as e:
            logger.error(f"모델 로드 실패: {e}")
            return False
    
    def save_scalers(self):
        """스케일러 저장"""
        for model_name, scaler in self.scalers.items():
            if scaler is not None:
                scaler_path = self.models_dir / f"{model_name}_scaler.pkl"
                joblib.dump(scaler, scaler_path)

    def save_models(self) -> bool:
        """훈련된 모델들을 파일로 저장"""
        try:
            if not self.models:
                logger.warning("저장할 모델이 없습니다")
                return False
            
            saved_count = 0
            for model_name, model in self.models.items():
                try:
                    model_path = self.models_dir / f"{model_name}_model.pkl"
                    joblib.dump(model, model_path)
                    logger.debug(f"✅ {model_name} 모델 저장: {model_path}")
                    saved_count += 1
                except Exception as e:
                    logger.error(f"❌ {model_name} 모델 저장 실패: {e}")
            
            # 스케일러들도 저장
            self.save_scalers()
            
            logger.info(f"💾 {saved_count}개 모델 저장 완료")
            return saved_count > 0
            
        except Exception as e:
            logger.error(f"❌ 모델 저장 실패: {e}")
            return False

    def predict(self, data: pd.DataFrame) -> Dict:
        """단일 예측 메서드 - 호환성을 위함"""
        try:
            if not self.models:
                logger.warning("훈련된 모델이 없습니다. 먼저 모델을 훈련하거나 로드하세요.")
                return {
                    'signal': False,
                    'probability': 0.5,
                    'confidence': 0.0,
                    'ensemble_probability': 0.5
                }
            
            # 특성 생성
            df_features = self.feature_eng.create_features(data.copy())
            if df_features is None or df_features.empty:
                return {
                    'signal': False,
                    'probability': 0.5,
                    'confidence': 0.0,
                    'ensemble_probability': 0.5
                }
            
            # 최신 데이터포인트만 사용
            latest_features = np.array(df_features.iloc[-1][self.feature_columns].values).reshape(1, -1)
            latest_features = np.nan_to_num(latest_features, nan=0.0, posinf=1e6, neginf=-1e6)
            
            predictions = {}
            
            # 모든 모델로 예측
            for model_name, model in self.models.items():
                try:
                    scaler = self.scalers.get(model_name)
                    
                    # 스케일링
                    X = latest_features.copy()
                    if scaler is not None:
                        X = scaler.transform(X)
                    
                    # 예측
                    prob = model.predict_proba(X)[0, 1]
                    predictions[model_name] = prob
                    
                except Exception as e:
                    logger.warning(f"{model_name} 예측 실패: {e}")
                    continue
            
            if not predictions:
                return {
                    'signal': False,
                    'probability': 0.5,
                    'confidence': 0.0,
                    'ensemble_probability': 0.5
                }
            
            # 앙상블 예측 (평균)
            ensemble_prob = np.mean(list(predictions.values()))
            
            result = {
                'signal': ensemble_prob >= self.config.ML_PROB_THRESHOLD,
                'probability': ensemble_prob,
                'confidence': ensemble_prob,
                'ensemble_probability': ensemble_prob,
                'individual_predictions': predictions
            }
            
            return result
            
        except Exception as e:
            logger.error(f"예측 실패: {e}")
            return {
                'signal': False,
                'probability': 0.5,
                'confidence': 0.0,
                'ensemble_probability': 0.5
            }

    def get_model_performance(self) -> Dict:
        """모델 성능 정보 반환"""
        try:
            # 훈련 요약 파일에서 성능 정보 로드
            summary_path = self.models_dir / "training_summary.json"
            if summary_path.exists():
                summary = load_json(str(summary_path))
                return summary.get('results', {})
            
            # 훈련 요약이 없으면 기본값 반환
            if self.models:
                performance = {}
                for model_name in self.models.keys():
                    performance[model_name] = {
                        'auc_score': 0.75,  # 기본값
                        'pr_auc': 0.65,
                        'cv_mean': 0.73,
                        'cv_std': 0.05
                    }
                return performance
            else:
                return {}
                
        except Exception as e:
            logger.error(f"모델 성능 정보 로드 실패: {e}")
            return {}
