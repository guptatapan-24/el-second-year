#!/usr/bin/env python3
"""Train XGBoost risk prediction model"""

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, precision_recall_curve, classification_report
import joblib
import json
import hashlib
from datetime import datetime
from database import SessionLocal, Snapshot

class ModelTrainer:
    def __init__(self):
        self.model = None
        self.feature_names = [
            'tvl', 'reserve0', 'reserve1', 'volume_24h',
            'tvl_pct_change_1h', 'reserve_imbalance',
            'volume_tvl_ratio', 'volatility_24h', 'leverage_ratio'
        ]
    
    def load_training_data(self) -> pd.DataFrame:
        """Load training data from database"""
        db = SessionLocal()
        try:
            snapshots = db.query(Snapshot).all()
            
            data = []
            for snap in snapshots:
                row = {
                    'pool_id': snap.pool_id,
                    'timestamp': snap.timestamp,
                    'tvl': snap.tvl or 0,
                    'reserve0': snap.reserve0 or 0,
                    'reserve1': snap.reserve1 or 0,
                    'volume_24h': snap.volume_24h or 0,
                }
                
                # Add derived features
                if snap.features:
                    for key in ['tvl_pct_change_1h', 'reserve_imbalance',
                               'volume_tvl_ratio', 'volatility_24h', 'leverage_ratio']:
                        row[key] = snap.features.get(key, 0)
                
                data.append(row)
            
            df = pd.DataFrame(data)
            print(f"Loaded {len(df)} snapshots from database")
            return df
        finally:
            db.close()
    
    def create_labels(self, df: pd.DataFrame) -> pd.Series:
        """
        Binary risk labels:
        1 = risky
        0 = safe
        """

        df = df.copy()

        # Ensure required columns exist
        for col in ["tvl_pct_change_1h", "reserve_imbalance", "volatility_24h"]:
            df[col] = df[col].fillna(0)

        # Hard binary rules
        risk = (
            (df["tvl_pct_change_1h"] <= -20) |
            (df["reserve_imbalance"] >= 0.30) |
            (df["volatility_24h"] >= 0.10)
        )

        labels = risk.astype(int)

        print("Label distribution:")
        print(labels.value_counts())

        return labels

    
    def train(self, df: pd.DataFrame, labels: pd.Series):
        """Train XGBoost model"""
        # Prepare features
        X = df[self.feature_names].fillna(0)
        y = labels
        
        split_idx = int(len(X) * 0.8)

        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

        # Fallback: if test set has only one class, reshuffle safely
        if y_test.nunique() < 2:
            print("⚠ Test set single-class, switching to stratified split")

            X_train, X_test, y_train, y_test = train_test_split(
                X, y,
                test_size=0.2,
                random_state=42,
                stratify=y
            )

        
        # Train XGBoost
        print("Training XGBoost model...")
        self.model = xgb.XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            # objective="binary:logistic",   # 🔥 IMPORTANT
            eval_metric="logloss",
            random_state=42,
        )


        
        self.model.fit(X_train, y_train)
        
        # Evaluate
        # Evaluate
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]
        y_pred = self.model.predict(X_test)

        metrics = {}

        if len(set(y_test)) > 1:
            auc = roc_auc_score(y_test, y_pred_proba)
            print(f"\nTest AUC: {auc:.4f}")
            metrics['auc'] = float(auc)
        else:
            print("\n⚠ ROC AUC skipped: single-class test set (expected with time-based split)")
            metrics['auc'] = None

        print("\nClassification Report:")
        print(classification_report(y_test, y_pred, zero_division=0))

        
        # Feature importance
        importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        print("\nFeature Importance:")
        print(importance)
        
        metrics.update({
        'n_train': len(X_train),
        'n_test': len(X_test),
        'feature_importance': importance.to_dict('records')
        })
        return metrics

    
    def save_model(self, metrics: dict, model_path: str = '../models/xgb_veririsk_v1.pkl'):
        """Save model and metadata"""
        # Save model
        joblib.dump(self.model, model_path)
        print(f"Model saved to {model_path}")
        
        # Compute model fingerprint
        with open(model_path, 'rb') as f:
            model_bytes = f.read()
            sha256 = hashlib.sha256(model_bytes).hexdigest()
        
        # Create metadata
        metadata = {
            'model_name': 'xgb_veririsk_v1',
            'sha256': sha256,
            'ipfs_cid': 'Qm...',  # To be updated after IPFS upload
            'train_date': datetime.utcnow().isoformat(),
            'metrics': metrics,
            'feature_names': self.feature_names,
            'model_type': 'XGBClassifier',
            'hyperparameters': {
                'n_estimators': 200,
                'max_depth': 6,
                'learning_rate': 0.05,
                'subsample': 0.8
            }
        }
        
        metadata_path = model_path.replace('.pkl', '_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"Metadata saved to {metadata_path}")
        
        return metadata

if __name__ == "__main__":
    trainer = ModelTrainer()
    
    # Load data
    df = trainer.load_training_data()
    
    if len(df) == 0:
        print("No training data found. Generate synthetic data first:")
        print("  python data_fetcher.py --synthetic")
        exit(1)
    
    # Create labels
    labels = trainer.create_labels(df)
    
    # Train
    metrics = trainer.train(df, labels)
    
    # Save
    metadata = trainer.save_model(metrics)
    print("\nTraining complete!")
    print(json.dumps(metadata, indent=2))
