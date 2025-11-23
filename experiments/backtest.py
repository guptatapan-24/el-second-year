#!/usr/bin/env python3
"""
Backtesting script for VeriRisk oracle
Evaluates model performance on historical data
"""

import sys
import os
sys.path.append('../backend')
os.chdir('../backend')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import (
    roc_auc_score, precision_recall_curve, roc_curve,
    classification_report, confusion_matrix
)
import joblib
from datetime import datetime, timedelta
from database import SessionLocal, Snapshot

class VeriRiskBacktest:
    def __init__(self, model_path='../models/xgb_veririsk_v1.pkl'):
        self.model = joblib.load(model_path)
        self.feature_names = [
            'tvl', 'reserve0', 'reserve1', 'volume_24h',
            'tvl_pct_change_1h', 'reserve_imbalance',
            'volume_tvl_ratio', 'volatility_24h', 'leverage_ratio'
        ]
        self.results = {}
    
    def load_historical_data(self):
        """Load all snapshots from database"""
        db = SessionLocal()
        try:
            snapshots = db.query(Snapshot).order_by(Snapshot.timestamp).all()
            
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
                
                if snap.features:
                    for key in ['tvl_pct_change_1h', 'reserve_imbalance',
                               'volume_tvl_ratio', 'volatility_24h', 'leverage_ratio']:
                        row[key] = snap.features.get(key, 0)
                
                data.append(row)
            
            df = pd.DataFrame(data)
            print(f"Loaded {len(df)} historical snapshots")
            return df
        finally:
            db.close()
    
    def create_labels(self, df):
        """Create ground truth labels for risk events"""
        df['tvl_pct_change_1h'] = df['tvl_pct_change_1h'].fillna(0)
        df['reserve_imbalance'] = df['reserve_imbalance'].fillna(0)
        df['volatility_24h'] = df['volatility_24h'].fillna(0)
        
        # High risk if any of these conditions
        labels = (
            (df['tvl_pct_change_1h'] < -20) |
            (df['reserve_imbalance'] > 0.3) |
            (df['volatility_24h'] > 0.1)
        ).astype(int)
        
        return labels
    
    def simulate_oracle_predictions(self, df, labels):
        """Simulate oracle predictions at each timestamp"""
        X = df[self.feature_names].fillna(0)
        
        # Get predictions and probabilities
        y_pred_proba = self.model.predict_proba(X)[:, 1]
        y_pred = self.model.predict(X)
        
        # Scale to 0-100 risk score
        risk_scores = y_pred_proba * 100
        
        # Add to dataframe
        df['risk_score'] = risk_scores
        df['predicted_risk'] = y_pred
        df['actual_risk'] = labels
        
        return df
    
    def calculate_metrics(self, df):
        """Calculate evaluation metrics"""
        y_true = df['actual_risk']
        y_pred = df['predicted_risk']
        y_pred_proba = df['risk_score'] / 100
        
        # ROC-AUC
        auc = roc_auc_score(y_true, y_pred_proba)
        
        # Precision-Recall
        precision, recall, thresholds = precision_recall_curve(y_true, y_pred_proba)
        
        # Classification report
        report = classification_report(y_true, y_pred, output_dict=True)
        
        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        
        self.results = {
            'auc': auc,
            'precision': precision,
            'recall': recall,
            'thresholds': thresholds,
            'classification_report': report,
            'confusion_matrix': cm
        }
        
        return self.results
    
    def calculate_lead_time(self, df):
        """Calculate lead time before risk events"""
        lead_times = []
        
        # Group by pool
        for pool_id in df['pool_id'].unique():
            pool_df = df[df['pool_id'] == pool_id].sort_values('timestamp')
            
            # Find risk events (actual_risk = 1)
            risk_events = pool_df[pool_df['actual_risk'] == 1]
            
            for event_idx in risk_events.index:
                event_time = pool_df.loc[event_idx, 'timestamp']
                
                # Look for warnings before the event
                prior_data = pool_df[
                    (pool_df['timestamp'] < event_time) &
                    (pool_df['predicted_risk'] == 1)
                ]
                
                if len(prior_data) > 0:
                    # Find earliest warning
                    earliest_warning = prior_data['timestamp'].min()
                    lead_time = (event_time - earliest_warning).total_seconds() / 3600  # hours
                    lead_times.append(lead_time)
        
        if lead_times:
            return {
                'mean_lead_time_hours': np.mean(lead_times),
                'median_lead_time_hours': np.median(lead_times),
                'min_lead_time_hours': np.min(lead_times),
                'max_lead_time_hours': np.max(lead_times),
                'total_warnings': len(lead_times)
            }
        else:
            return {'total_warnings': 0}
    
    def plot_roc_curve(self, save_path='results/roc_curve.png'):
        """Plot ROC curve"""
        import os
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        plt.figure(figsize=(8, 6))
        plt.plot([0, 1], [0, 1], 'k--', label='Random (AUC=0.5)')
        
        # We can compute ROC from stored precision/recall
        # For now, just show the AUC score
        plt.text(0.6, 0.3, f"AUC = {self.results['auc']:.4f}", 
                fontsize=14, bbox=dict(boxstyle='round', facecolor='wheat'))
        
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title('ROC Curve - VeriRisk Oracle')
        plt.legend()
        plt.grid(alpha=0.3)
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"ROC curve saved to {save_path}")
    
    def print_summary(self):
        """Print backtesting summary"""
        print("\n" + "="*60)
        print("VERIRISK BACKTESTING RESULTS")
        print("="*60)
        
        print(f"\n📊 Model Performance:")
        print(f"  AUC-ROC:     {self.results['auc']:.4f}")
        
        report = self.results['classification_report']
        print(f"\n  Precision:   {report['1']['precision']:.4f} (high risk class)")
        print(f"  Recall:      {report['1']['recall']:.4f} (high risk class)")
        print(f"  F1-Score:    {report['1']['f1-score']:.4f}")
        print(f"  Accuracy:    {report['accuracy']:.4f}")
        
        cm = self.results['confusion_matrix']
        print(f"\n📈 Confusion Matrix:")
        print(f"  True Negatives:  {cm[0][0]} (correct low risk predictions)")
        print(f"  False Positives: {cm[0][1]} (false alarms)")
        print(f"  False Negatives: {cm[1][0]} (missed risks)")
        print(f"  True Positives:  {cm[1][1]} (correct high risk predictions)")
        
        if hasattr(self, 'lead_time_stats'):
            print(f"\n⏱️  Lead Time Analysis:")
            stats = self.lead_time_stats
            if stats.get('total_warnings', 0) > 0:
                print(f"  Mean lead time:   {stats['mean_lead_time_hours']:.2f} hours")
                print(f"  Median lead time: {stats['median_lead_time_hours']:.2f} hours")
                print(f"  Min lead time:    {stats['min_lead_time_hours']:.2f} hours")
                print(f"  Max lead time:    {stats['max_lead_time_hours']:.2f} hours")
                print(f"  Total warnings:   {stats['total_warnings']}")
            else:
                print("  No warnings issued before risk events")
        
        print("\n" + "="*60)
    
    def run_full_backtest(self):
        """Run complete backtesting workflow"""
        print("Starting VeriRisk Backtesting...")
        
        # Load data
        df = self.load_historical_data()
        
        # Create labels
        labels = self.create_labels(df)
        print(f"Risk event distribution: {labels.value_counts().to_dict()}")
        
        # Simulate predictions
        df = self.simulate_oracle_predictions(df, labels)
        
        # Calculate metrics
        self.calculate_metrics(df)
        
        # Calculate lead time
        self.lead_time_stats = self.calculate_lead_time(df)
        
        # Plot results
        self.plot_roc_curve()
        
        # Print summary
        self.print_summary()
        
        # Save results
        import json
        results_summary = {
            'auc': float(self.results['auc']),
            'classification_report': {
                k: {kk: float(vv) if isinstance(vv, (int, float)) else vv 
                    for kk, vv in v.items()} if isinstance(v, dict) else v
                for k, v in self.results['classification_report'].items()
            },
            'confusion_matrix': self.results['confusion_matrix'].tolist(),
            'lead_time_stats': self.lead_time_stats,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        with open('results/backtest_results.json', 'w') as f:
            json.dump(results_summary, f, indent=2)
        print("\nResults saved to results/backtest_results.json")
        
        return df, self.results


if __name__ == "__main__":
    backtester = VeriRiskBacktest()
    df, results = backtester.run_full_backtest()
    
    print("\n✅ Backtesting complete!")
