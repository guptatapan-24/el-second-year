#!/usr/bin/env python3
"""
VeriRisk Phase-2: Predictive Risk Model Trainer

This module implements forward-looking crash prediction using:
1. Forward labels (t+6h, t+24h TVL drop predictions)
2. Time-aware train/test split (no shuffling, no data leakage)
3. Advanced predictive features
4. Class imbalance handling with scale_pos_weight

Academic Design:
- Predicts FUTURE crashes, not current risk state
- No data leakage: labels computed from future data, features from past only
- Time-series aware: train on past, test on future
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import (
    roc_auc_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix
)
import joblib
import json
import hashlib
from datetime import datetime
from typing import Dict, Tuple, Optional
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, Snapshot
from features.advanced_features import AdvancedFeatureEngine


class PredictiveModelTrainer:
    """
    Trainer for predictive risk model that forecasts future TVL crashes.
    
    Key differences from Phase-1:
    - Forward-looking labels (predicts future, not current)
    - Time-aware split (no shuffling)
    - Advanced predictive features
    """
    
    # Prediction horizons (in hours, assuming hourly data)
    HORIZON_6H = 6
    HORIZON_24H = 24
    
    # Crash thresholds
    CRASH_THRESHOLD_6H = 0.10   # 10% drop in 6 hours
    CRASH_THRESHOLD_24H = 0.20  # 20% drop in 24 hours
    
    def __init__(self):
        self.model = None
        self.feature_engine = AdvancedFeatureEngine()
        self.feature_names = AdvancedFeatureEngine.get_feature_names()
        
    def load_training_data(self) -> pd.DataFrame:
        """
        Load all snapshots from database and prepare for training.
        
        Returns DataFrame with columns:
        - pool_id, timestamp, tvl, volume_24h, reserve0, reserve1
        """
        db = SessionLocal()
        try:
            snapshots = db.query(Snapshot).all()
            
            data = []
            for snap in snapshots:
                row = {
                    'pool_id': snap.pool_id,
                    'timestamp': snap.timestamp,
                    'tvl': float(snap.tvl or 0),
                    'reserve0': float(snap.reserve0 or 0),
                    'reserve1': float(snap.reserve1 or 0),
                    'volume_24h': float(snap.volume_24h or 0),
                }
                data.append(row)
            
            df = pd.DataFrame(data)
            
            if len(df) == 0:
                print("⚠ No training data found")
                return df
                
            # Sort by pool_id and timestamp (critical for forward labels)
            df = df.sort_values(['pool_id', 'timestamp']).reset_index(drop=True)
            
            print(f"✓ Loaded {len(df)} snapshots from {df['pool_id'].nunique()} pools")
            return df
            
        finally:
            db.close()
    
    def create_forward_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create forward-looking labels for crash prediction.
        
        Labels:
        - label_6h:  1 if TVL drops >10% in next 6 hours, 0 otherwise
        - label_24h: 1 if TVL drops >20% in next 24 hours, 0 otherwise
        
        CRITICAL: Labels use FUTURE TVL values only - no data leakage.
        
        Args:
            df: DataFrame sorted by pool_id and timestamp
            
        Returns:
            DataFrame with label columns added
        """
        df = df.copy()
        
        # Initialize label columns
        df['label_6h'] = np.nan
        df['label_24h'] = np.nan
        
        # Process each pool separately
        for pool_id in df['pool_id'].unique():
            mask = df['pool_id'] == pool_id
            pool_df = df.loc[mask].copy()
            
            # Get TVL series
            tvl = pool_df['tvl'].values
            n = len(tvl)
            
            # Compute forward returns (future TVL change)
            # For each point t, look at TVL at t+6 and t+24
            for horizon, threshold, label_col in [
                (self.HORIZON_6H, self.CRASH_THRESHOLD_6H, 'label_6h'),
                (self.HORIZON_24H, self.CRASH_THRESHOLD_24H, 'label_24h')
            ]:
                labels = np.zeros(n)
                
                for i in range(n - horizon):
                    current_tvl = tvl[i]
                    future_tvl = tvl[i + horizon]
                    
                    if current_tvl > 0:
                        # Forward return (negative = drop)
                        forward_return = (future_tvl - current_tvl) / current_tvl
                        
                        # Label = 1 if drop exceeds threshold
                        if forward_return < -threshold:
                            labels[i] = 1
                
                # Mark last `horizon` rows as NaN (no future data available)
                labels[-horizon:] = np.nan
                
                df.loc[mask, label_col] = labels
        
        # Drop rows with NaN labels (at the end of each pool's series)
        valid_mask = df['label_24h'].notna()
        df_labeled = df[valid_mask].copy()
        
        # Print label distribution
        print("\n📊 Label Distribution (primary target: label_24h)")
        print(f"   label_24h: {int(df_labeled['label_24h'].sum())} crashes / {len(df_labeled)} total")
        print(f"   label_6h:  {int(df_labeled['label_6h'].sum())} crashes / {len(df_labeled)} total")
        
        crash_rate_24h = df_labeled['label_24h'].mean() * 100
        crash_rate_6h = df_labeled['label_6h'].mean() * 100
        print(f"   Crash rate (24h): {crash_rate_24h:.1f}%")
        print(f"   Crash rate (6h):  {crash_rate_6h:.1f}%")
        
        return df_labeled
    
    def compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute all predictive features for the dataset.
        
        Features are backward-looking (use only past data) to prevent leakage.
        
        Args:
            df: DataFrame with raw metrics
            
        Returns:
            DataFrame with feature columns added
        """
        print("\n🔧 Computing predictive features...")
        
        all_dfs = []
        
        for pool_id in df['pool_id'].unique():
            pool_df = df[df['pool_id'] == pool_id].copy()
            pool_df = self.feature_engine.compute_features_from_df(pool_df, pool_id)
            all_dfs.append(pool_df)
        
        df_features = pd.concat(all_dfs, ignore_index=True)
        
        print(f"   ✓ Computed {len(self.feature_names)} features for {len(df_features)} samples")
        
        return df_features
    
    def prepare_training_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
        """
        Full pipeline: load data, create labels, compute features.
        
        Returns:
            Tuple of (features_df, labels_24h, labels_6h)
        """
        # Create forward labels
        df_labeled = self.create_forward_labels(df)
        
        if len(df_labeled) == 0:
            raise ValueError("No valid labeled data after forward label creation")
        
        # Compute features
        df_features = self.compute_features(df_labeled)
        
        # Extract features and labels
        X = df_features[self.feature_names].fillna(0)
        y_24h = df_features['label_24h'].astype(int)
        y_6h = df_features['label_6h'].astype(int)
        
        return X, y_24h, y_6h, df_features
    
    def train(self, X: pd.DataFrame, y: pd.Series, 
              train_ratio: float = 0.8) -> Dict:
        """
        Train XGBoost classifier with time-aware split.
        
        CRITICAL: No shuffling - train on earlier data, test on later data.
        This simulates real-world prediction where we predict future from past.
        
        Args:
            X: Feature DataFrame
            y: Target labels (binary)
            train_ratio: Fraction of data for training (default 0.8)
            
        Returns:
            Dictionary of evaluation metrics
        """
        print("\n🎯 Training Predictive Model...")
        print("   Target: label_24h (TVL crash >20% in next 24 hours)")
        
        # TIME-AWARE SPLIT (critical for no data leakage)
        split_idx = int(len(X) * train_ratio)
        
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        
        print(f"   Train size: {len(X_train)}")
        print(f"   Test size:  {len(X_test)}")
        print(f"   Train crash rate: {y_train.mean()*100:.1f}%")
        print(f"   Test crash rate:  {y_test.mean()*100:.1f}%")
        
        # Handle class imbalance with scale_pos_weight
        # scale_pos_weight = num_negative / num_positive
        n_pos = y_train.sum()
        n_neg = len(y_train) - n_pos
        scale_pos_weight = n_neg / max(n_pos, 1)
        
        print(f"   Class imbalance ratio: {scale_pos_weight:.2f}")
        
        # Train XGBoost
        self.model = xgb.XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_weight,
            eval_metric='logloss',
            random_state=42,
            use_label_encoder=False
        )
        
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )
        
        # Evaluate
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]
        y_pred = self.model.predict(X_test)
        
        metrics = self._compute_metrics(y_test, y_pred, y_pred_proba)
        
        # Print results
        self._print_evaluation_results(y_test, y_pred, y_pred_proba, metrics)
        
        # Feature importance
        self._print_feature_importance()
        
        metrics.update({
            'n_train': len(X_train),
            'n_test': len(X_test),
            'train_crash_rate': float(y_train.mean()),
            'test_crash_rate': float(y_test.mean()),
            'scale_pos_weight': float(scale_pos_weight),
        })
        
        return metrics
    
    def _compute_metrics(self, y_true: pd.Series, y_pred: np.ndarray, 
                         y_pred_proba: np.ndarray) -> Dict:
        """Compute evaluation metrics."""
        metrics = {}
        
        # ROC-AUC (if both classes present)
        if len(set(y_true)) > 1:
            metrics['roc_auc'] = float(roc_auc_score(y_true, y_pred_proba))
        else:
            metrics['roc_auc'] = None
            
        # Precision, Recall, F1
        metrics['precision'] = float(precision_score(y_true, y_pred, zero_division=0))
        metrics['recall'] = float(recall_score(y_true, y_pred, zero_division=0))
        metrics['f1_score'] = float(f1_score(y_true, y_pred, zero_division=0))
        
        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        metrics['confusion_matrix'] = cm.tolist()
        
        return metrics
    
    def _print_evaluation_results(self, y_true, y_pred, y_pred_proba, metrics):
        """Print formatted evaluation results."""
        print("\n📈 Model Evaluation Results:")
        print("="*50)
        
        if metrics['roc_auc']:
            print(f"   ROC-AUC:   {metrics['roc_auc']:.4f}")
        else:
            print("   ROC-AUC:   N/A (single class in test set)")
            
        print(f"   Precision: {metrics['precision']:.4f}")
        print(f"   Recall:    {metrics['recall']:.4f}")
        print(f"   F1-Score:  {metrics['f1_score']:.4f}")
        
        print("\n   Classification Report:")
        print(classification_report(y_true, y_pred, 
                                    target_names=['No Crash', 'Crash'],
                                    zero_division=0))
        
        print("   Confusion Matrix:")
        cm = metrics['confusion_matrix']
        print("                 Predicted")
        print("                 No Crash  Crash")
        print(f"   Actual No Crash  {cm[0][0]:5d}  {cm[0][1]:5d}")
        print(f"   Actual Crash     {cm[1][0]:5d}  {cm[1][1]:5d}")
    
    def _print_feature_importance(self):
        """Print feature importance ranking."""
        importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print("\n📊 Feature Importance:")
        for _, row in importance.head(10).iterrows():
            bar = '█' * int(row['importance'] * 50)
            print(f"   {row['feature']:25s} {row['importance']:.4f} {bar}")
        
        return importance.to_dict('records')
    
    def save_model(self, metrics: Dict, 
                   model_path: str = '../models/xgb_veririsk_v2_predictive.pkl') -> Dict:
        """
        Save trained model and metadata.
        
        Args:
            metrics: Training metrics dictionary
            model_path: Path to save model
            
        Returns:
            Metadata dictionary
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        # Save model
        joblib.dump(self.model, model_path)
        print(f"\n💾 Model saved to {model_path}")
        
        # Compute model fingerprint
        with open(model_path, 'rb') as f:
            model_bytes = f.read()
            sha256 = hashlib.sha256(model_bytes).hexdigest()
        
        # Feature importance
        importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        # Create metadata
        metadata = {
            'model_name': 'xgb_veririsk_v2_predictive',
            'model_version': 'v2.0',
            'model_type': 'XGBClassifier',
            'prediction_task': 'binary_classification',
            'prediction_target': 'TVL crash >20% in next 24 hours',
            'prediction_horizon': '24 hours',
            'secondary_target': 'TVL crash >10% in next 6 hours',
            'sha256': sha256,
            'ipfs_cid': 'Qm...',  # To be updated after IPFS upload
            'train_date': datetime.utcnow().isoformat(),
            'metrics': metrics,
            'feature_names': self.feature_names,
            'feature_importance': importance.to_dict('records'),
            'hyperparameters': {
                'n_estimators': 300,
                'max_depth': 6,
                'learning_rate': 0.05,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'scale_pos_weight': metrics.get('scale_pos_weight', 1.0)
            },
            'design_notes': {
                'label_type': 'forward_looking',
                'train_test_split': 'time_based_no_shuffle',
                'data_leakage_prevention': 'features use only past data, labels use only future data'
            }
        }
        
        metadata_path = model_path.replace('.pkl', '_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"   Metadata saved to {metadata_path}")
        
        return metadata


def main():
    """Main training pipeline."""
    print("="*60)
    print("VeriRisk Phase-2: Predictive Risk Model Training")
    print("="*60)
    
    trainer = PredictiveModelTrainer()
    
    # Load data
    df = trainer.load_training_data()
    
    if len(df) == 0:
        print("\n⚠ No training data found. Generate synthetic data first:")
        print("   python data_fetcher.py --predictive")
        return
    
    if len(df) < 100:
        print(f"\n⚠ Insufficient data ({len(df)} samples). Need at least 100.")
        print("   Run: python data_fetcher.py --predictive")
        return
    
    # Prepare training data (labels + features)
    try:
        X, y_24h, y_6h, df_full = trainer.prepare_training_data(df)
    except ValueError as e:
        print(f"\n⚠ Error preparing data: {e}")
        return
    
    # Check label distribution
    if y_24h.sum() == 0:
        print("\n⚠ No positive labels (crashes) found. Generate more varied data:")
        print("   python data_fetcher.py --predictive")
        return
    
    # Train on primary target (24h)
    metrics = trainer.train(X, y_24h)
    
    # Save model
    metadata = trainer.save_model(metrics)
    
    print("\n" + "="*60)
    print("✅ Training Complete!")
    print("="*60)
    print(f"\nModel: {metadata['model_name']}")
    print(f"Target: {metadata['prediction_target']}")
    if metrics.get('roc_auc'):
        print(f"ROC-AUC: {metrics['roc_auc']:.4f}")
    print(f"F1-Score: {metrics['f1_score']:.4f}")
    print("\nRun inference with:")
    print("   python model_server.py --run-once --pool test_pool_1")


if __name__ == "__main__":
    main()
