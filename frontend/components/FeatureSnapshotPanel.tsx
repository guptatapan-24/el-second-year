import { motion } from 'framer-motion';
import { Database, TrendingUp, DollarSign, Activity, BarChart3, Percent } from 'lucide-react';

interface FeatureSnapshot {
  tvl: number;
  volume_24h: number;
  reserve_imbalance?: number;
  volatility?: number;
  leverage_ratio?: number;
  liquidity_depth?: number;
  fee_apy?: number;
}

interface FeatureSnapshotPanelProps {
  features: FeatureSnapshot;
  loading?: boolean;
}

const formatCurrency = (value: number) => {
  if (value >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(2)}B`;
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(2)}K`;
  return `$${value.toFixed(2)}`;
};

const formatPercent = (value: number) => `${(value * 100).toFixed(2)}%`;

const featureConfig: Record<string, { label: string; icon: any; format: (v: number) => string }> = {
  tvl: { label: 'Total Value Locked', icon: DollarSign, format: formatCurrency },
  volume_24h: { label: '24h Volume', icon: TrendingUp, format: formatCurrency },
  reserve_imbalance: { label: 'Reserve Imbalance', icon: BarChart3, format: formatPercent },
  volatility: { label: 'Price Volatility', icon: Activity, format: formatPercent },
  leverage_ratio: { label: 'Leverage Ratio', icon: TrendingUp, format: (v) => v.toFixed(2) + 'x' },
  liquidity_depth: { label: 'Liquidity Depth', icon: Database, format: formatCurrency },
  fee_apy: { label: 'Fee APY', icon: Percent, format: formatPercent },
};

export default function FeatureSnapshotPanel({ features, loading }: FeatureSnapshotPanelProps) {
  if (loading) {
    return (
      <div className="glass-card p-6">
        <div className="h-6 w-40 bg-dark-600 rounded shimmer-loading mb-4" />
        <div className="grid grid-cols-2 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="p-3 bg-dark-700 rounded-lg">
              <div className="h-3 w-20 bg-dark-600 rounded shimmer-loading mb-2" />
              <div className="h-5 w-16 bg-dark-600 rounded shimmer-loading" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  const displayFeatures = Object.entries(features)
    .filter(([key, value]) => value !== undefined && value !== null && featureConfig[key])
    .map(([key, value]) => ({
      key,
      value: value as number,
      ...featureConfig[key],
    }));

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-6"
      data-testid="feature-snapshot"
    >
      <div className="flex items-center gap-2 mb-4">
        <div className="w-8 h-8 rounded-lg bg-defi-primary/20 flex items-center justify-center">
          <Database className="w-4 h-4 text-defi-primary" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-white">Feature Snapshot</h3>
          <p className="text-xs text-gray-500">Raw model input values</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {displayFeatures.map((feature, idx) => {
          const Icon = feature.icon;
          return (
            <motion.div
              key={feature.key}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: idx * 0.05 }}
              className="p-3 bg-dark-800/50 rounded-lg border border-white/5 hover:border-defi-primary/30 transition-colors"
            >
              <div className="flex items-center gap-2 mb-1">
                <Icon className="w-3 h-3 text-gray-500" />
                <span className="text-[10px] text-gray-500 uppercase tracking-wider">
                  {feature.label}
                </span>
              </div>
              <div className="text-sm font-semibold text-white">
                {feature.format(feature.value)}
              </div>
            </motion.div>
          );
        })}
      </div>

      <div className="mt-4 pt-4 border-t border-white/5">
        <p className="text-xs text-gray-500">
          These values are fed into the XGBoost model for risk prediction.
        </p>
      </div>
    </motion.div>
  );
}
