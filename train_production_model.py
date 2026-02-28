#!/usr/bin/env python3
"""
프로덕션 ML 모델 훈련 - 새로운 대용량 데이터셋 사용
"""

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from loguru import logger
import joblib
import json

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.ensemble import RandomForestClassifier

try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False
    logger.warning("XGBoost 없음")

from config import load_config
from utils import ensure_dir

def train_production_model():
    """프로덕션용 ML 모델 훈련"""
    logger.info("🚀 프로덕션 ML 모델 훈련 시작")
    
    try:
        # 1. 최신 데이터셋 자동 선택
        dataset_dir = Path("advanced_datasets")
        dataset_files = list(dataset_dir.glob("*.csv"))
        
        if not dataset_files:
            logger.error("❌ 데이터셋 파일이 없습니다")
            return False
        
        # 가장 최근 파일 선택
        latest_file = max(dataset_files, key=lambda f: f.stat().st_mtime)
        dataset_path = str(latest_file)
        
        logger.info(f"📂 최신 데이터셋 로드: {dataset_path}")
        
        # 청크로 읽기 (큰 파일)
        chunk_size = 10000
        chunks = []
        for chunk in pd.read_csv(dataset_path, chunksize=chunk_size):
            chunks.append(chunk)
        
        df = pd.concat(chunks, ignore_index=True)
        logger.info(f"✅ 데이터 로드 완료: {len(df):,}행")
        
        # 2. 타겟 확인
        if 'surge_target' in df.columns:
            target_col = 'surge_target'
        else:
            logger.error("❌ surge_target 컬럼이 없습니다")
            return False
        
        # 3. 특성 선택
        exclude_cols = [
            'symbol', 'timestamp', 'surge_target',
            'future_high', 'future_return'
        ] + [col for col in df.columns if 'surge_' in col and col != 'surge_target']
        
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        
        # 4. 데이터 정리
        df_clean = df[feature_cols + [target_col]].dropna()
        df_clean = df_clean.replace([np.inf, -np.inf], np.nan).dropna()
        
        logger.info(f"🔧 정리된 데이터: {len(df_clean):,}행, {len(feature_cols)}개 특성")
        
        # 5. X, y 분리
        X = df_clean[feature_cols].values
        y = df_clean[target_col].values.astype(int)
        
        # 타겟 분포
        unique, counts = np.unique(y, return_counts=True)
        for val, count in zip(unique, counts):
            pct = count / len(y) * 100
            logger.info(f"클래스 {val}: {count:,}개 ({pct:.1f}%)")
        
        # 6. 데이터 분할
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        logger.info(f"📊 훈련: {len(X_train):,}, 테스트: {len(X_test):,}")
        
        # 7. 모델 훈련
        results = {}
        models_dir = ensure_dir("models")
        
        # RandomForest
        logger.info("🌳 RandomForest 훈련 중...")
        rf = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        rf.fit(X_train, y_train)
        
        # 평가
        y_pred_proba = rf.predict_proba(X_test)[:, 1]
        auc_score = roc_auc_score(y_test, y_pred_proba)
        
        logger.info(f"✅ RandomForest AUC: {auc_score:.3f}")
        
        # 모델 저장
        rf_path = models_dir / "random_forest_model_new.pkl"
        joblib.dump(rf, rf_path)
        
        results['random_forest'] = {
            'auc_score': auc_score,
            'model_file': rf_path.name
        }
        
        # XGBoost (가능한 경우)
        if XGB_AVAILABLE:
            logger.info("⚡ XGBoost 훈련 중...")
            xgb_model = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                random_state=42
            )
            xgb_model.fit(X_train, y_train)
            
            # 평가
            y_pred_proba_xgb = xgb_model.predict_proba(X_test)[:, 1]
            auc_score_xgb = roc_auc_score(y_test, y_pred_proba_xgb)
            
            logger.info(f"✅ XGBoost AUC: {auc_score_xgb:.3f}")
            
            # 모델 저장
            xgb_path = models_dir / "xgboost_model_new.pkl"
            joblib.dump(xgb_model, xgb_path)
            
            results['xgboost'] = {
                'auc_score': auc_score_xgb,
                'model_file': xgb_path.name
            }
        
        # 8. 최고 성능 모델 선택
        best_model = max(results.keys(), key=lambda k: results[k]['auc_score'])
        best_auc = results[best_model]['auc_score']
        
        logger.success(f"🏆 최고 성능: {best_model} (AUC: {best_auc:.3f})")
        
        # 9. 훈련 요약 저장
        summary = {
            'timestamp': datetime.now().isoformat(),
            'dataset_size': len(df_clean),
            'feature_count': len(feature_cols),
            'feature_columns': feature_cols,
            'best_model': best_model,
            'best_auc': best_auc,
            'results': results
        }
        
        summary_path = models_dir / "training_summary_new.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.success(f"🎉 모델 훈련 완료! 최고 AUC: {best_auc:.3f}")
        return True
        
    except Exception as e:
        logger.error(f"❌ 모델 훈련 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = train_production_model()
    if success:
        print("✅ 프로덕션 모델 훈련 성공!")
    else:
        print("❌ 모델 훈련 실패")
