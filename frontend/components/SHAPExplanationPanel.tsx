import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Info } from 'lucide-react';

interface Reason {
  feature: string;
  impact: number;
  direction?: string;
  explanation?: string;
}

interface SHAPExplanationPanelProps {
  reasons: Reason[];
  loading?: boolean;
}

const featureExplanations: Record<string, string> = {
  tvl_change_1h: 'Significant TVL changes indicate potential instability',
  volume_volatility: 'High trading volume volatility suggests market stress',
  reserve_imbalance: 'Imbalanced reserves increase impermanent loss risk',
  leverage_ratio: 'High leverage amplifies liquidation risk',
  price_volatility: 'Price swings affect pool stability',
  liquidity_depth: 'Shallow liquidity leads to high slippage',
  tvl_velocity: 'Rapid TVL movement signals concern',
  fee_apy: 'Unusual APY may indicate unsustainable incentives',
};

export default function SHAPExplanationPanel({ reasons, loading }: SHAPExplanationPanelProps) {
  if (loading) {
    return (
      <div className="glass-card p-6 space-y-4">
        <div className="h-6 w-48 bg-dark-600 rounded shimmer-loading" />
        {[1, 2, 3].map((i) => (
          <div key={i} className="space-y-2">
            <div className="h-4 w-32 bg-dark-600 rounded shimmer-loading" />
            <div className="h-3 w-full bg-dark-600 rounded shimmer-loading" />
          </div>
        ))}
      </div>
    );
  }

  if (!reasons || reasons.length === 0) {
    return (
      <div className="glass-card p-6 text-center">
        <Info className="w-8 h-8 text-gray-500 mx-auto mb-2" />
        <p className="text-gray-400">No explanation data available</p>
      </div>
    );
  }

  const maxImpact = Math.max(...reasons.map((r) => Math.abs(r.impact)));

  return (
    <div className="glass-card p-6" data-testid="shap-panel">
      <div className="flex items-center gap-2 mb-6">
        <div className="w-8 h-8 rounded-lg bg-defi-secondary/20 flex items-center justify-center">
          <Info className="w-4 h-4 text-defi-secondary" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-white">SHAP Explanation</h3>
          <p className="text-xs text-gray-500">AI-powered risk factor analysis</p>
        </div>
      </div>

      <div className="space-y-4">
        {reasons.slice(0, 5).map((reason, idx) => {
          const isPositive = reason.impact > 0;
          const barWidth = (Math.abs(reason.impact) / maxImpact) * 100;
          const featureName = reason.feature.replace(/_/g, ' ');
          const explanation = featureExplanations[reason.feature] || reason.explanation || '';

          return (
            <motion.div
              key={reason.feature}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.1 }}
              className="group"
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  {isPositive ? (
                    <TrendingUp className="w-4 h-4 text-risk-high" />
                  ) : (
                    <TrendingDown className="w-4 h-4 text-risk-low" />
                  )}
                  <span className="text-sm font-medium text-white capitalize">
                    {featureName}
                  </span>
                </div>
                <span
                  className={`text-sm font-mono font-bold ${
                    isPositive ? 'text-risk-high' : 'text-risk-low'
                  }`}
                >
                  {isPositive ? '+' : ''}
                  {reason.impact.toFixed(3)}
                </span>
              </div>

              {/* Impact bar */}
              <div className="relative h-2 bg-dark-600 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${barWidth}%` }}
                  transition={{ duration: 0.8, delay: idx * 0.1, ease: 'easeOut' }}
                  className={`h-full rounded-full ${
                    isPositive
                      ? 'bg-gradient-to-r from-risk-high/50 to-risk-high'
                      : 'bg-gradient-to-r from-risk-low/50 to-risk-low'
                  }`}
                />
              </div>

              {/* Explanation tooltip on hover */}
              {explanation && (
                <p className="text-xs text-gray-500 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  {explanation}
                </p>
              )}
            </motion.div>
          );
        })}
      </div>

      <div className="mt-6 pt-4 border-t border-white/5">
        <p className="text-xs text-gray-500">
          <strong className="text-gray-400">SHAP values</strong> show how each feature
          contributes to the risk prediction. Positive values increase risk.
        </p>
      </div>
    </div>
  );
}
