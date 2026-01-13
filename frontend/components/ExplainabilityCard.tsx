import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Info, MessageSquare, Lightbulb } from 'lucide-react';
import ConfidenceBadge from './ConfidenceBadge';

interface EnhancedReason {
  feature: string;
  impact: number;
  direction: string;
  readable_name?: string;
  description?: string;
  explanation?: string;
}

interface Explainability {
  summary: string;
  top_factors: string[];
  risk_direction_hint: string;
}

interface ExplainabilityCardProps {
  reasons: EnhancedReason[];
  explainability?: Explainability;
  confidence?: string;
  confidenceReason?: string;
  loading?: boolean;
}

const featureTooltips: Record<string, string> = {
  tvl: 'Total Value Locked - Total assets deposited',
  tvl_change_6h: '6-hour TVL change - Recent trend indicator',
  tvl_change_24h: '24-hour TVL change - Daily trend',
  tvl_acceleration: 'Rate of change acceleration - Panic indicator',
  volume_24h: 'Trading volume in last 24 hours',
  volume_spike_ratio: 'Current vs average volume ratio',
  reserve_imbalance: 'Pool reserve balance ratio',
  reserve_imbalance_rate: 'Rate of imbalance change',
  volatility_6h: 'Short-term price volatility',
  volatility_24h: 'Long-term price volatility',
  volatility_ratio: 'Short vs long-term volatility',
  early_warning_score: 'Composite risk signal (0-100)',
};

export default function ExplainabilityCard({ 
  reasons, 
  explainability,
  confidence,
  confidenceReason,
  loading 
}: ExplainabilityCardProps) {
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
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-6"
      data-testid="explainability-card"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-defi-secondary/20 flex items-center justify-center">
            <Lightbulb className="w-4 h-4 text-defi-secondary" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Risk Explanation</h3>
            <p className="text-xs text-gray-500">AI-powered factor analysis</p>
          </div>
        </div>
        {confidence && (
          <ConfidenceBadge 
            confidence={confidence} 
            reason={confidenceReason}
            size="sm"
          />
        )}
      </div>

      {/* Natural Language Summary */}
      {explainability?.summary && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="mb-6 p-4 bg-dark-700/50 rounded-xl border border-white/5"
        >
          <div className="flex items-start gap-3">
            <MessageSquare className="w-5 h-5 text-defi-primary mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm text-gray-200 leading-relaxed">
                {explainability.summary}
              </p>
              {explainability.risk_direction_hint && (
                <p className="text-xs text-defi-primary mt-2 font-medium">
                  💡 {explainability.risk_direction_hint}
                </p>
              )}
            </div>
          </div>
        </motion.div>
      )}

      {/* Risk Factors */}
      <div className="space-y-4">
        {reasons.slice(0, 5).map((reason, idx) => {
          const isPositive = reason.impact > 0;
          const barWidth = (Math.abs(reason.impact) / maxImpact) * 100;
          const displayName = reason.readable_name || reason.feature.replace(/_/g, ' ');
          const tooltip = featureTooltips[reason.feature] || reason.description || '';

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
                  <motion.div
                    animate={{ 
                      y: isPositive ? [-1, 1, -1] : [1, -1, 1]
                    }}
                    transition={{ 
                      duration: 1.5, 
                      repeat: Infinity,
                      ease: 'easeInOut'
                    }}
                  >
                    {isPositive ? (
                      <TrendingUp className="w-4 h-4 text-risk-high" />
                    ) : (
                      <TrendingDown className="w-4 h-4 text-risk-low" />
                    )}
                  </motion.div>
                  <span className="text-sm font-medium text-white capitalize">
                    {displayName}
                  </span>
                  {/* Tooltip indicator */}
                  <div className="relative">
                    <Info className="w-3 h-3 text-gray-500 cursor-help" />
                    {tooltip && (
                      <div className="
                        absolute bottom-full left-1/2 -translate-x-1/2 mb-2
                        px-3 py-2 rounded-lg bg-dark-700 border border-white/10
                        text-xs text-gray-300 w-48
                        opacity-0 group-hover:opacity-100
                        pointer-events-none
                        transition-opacity duration-200
                        z-50
                      ">
                        {tooltip}
                      </div>
                    )}
                  </div>
                </div>
                <span
                  className={`text-sm font-mono font-bold ${
                    isPositive ? 'text-risk-high' : 'text-risk-low'
                  }`}
                >
                  {isPositive ? '+' : ''}{reason.impact.toFixed(3)}
                </span>
              </div>

              {/* Impact bar with smooth animation */}
              <div className="relative h-2 bg-dark-600 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${barWidth}%` }}
                  transition={{ 
                    duration: 0.8, 
                    delay: idx * 0.1, 
                    ease: [0.4, 0, 0.2, 1]  // ease-in-out
                  }}
                  className={`h-full rounded-full ${
                    isPositive
                      ? 'bg-gradient-to-r from-risk-high/50 to-risk-high'
                      : 'bg-gradient-to-r from-risk-low/50 to-risk-low'
                  }`}
                />
              </div>

              {/* Description on hover */}
              {reason.description && (
                <p className="text-xs text-gray-500 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  {reason.description}
                </p>
              )}
            </motion.div>
          );
        })}
      </div>

      {/* Top Factors List */}
      {explainability?.top_factors && explainability.top_factors.length > 0 && (
        <div className="mt-6 pt-4 border-t border-white/5">
          <h4 className="text-xs text-gray-500 mb-3 font-medium">Key Factors Summary</h4>
          <ul className="space-y-2">
            {explainability.top_factors.map((factor, idx) => (
              <motion.li 
                key={idx}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + idx * 0.1 }}
                className="text-sm text-gray-300 flex items-start gap-2"
              >
                <span className="text-defi-primary mt-1">•</span>
                {factor}
              </motion.li>
            ))}
          </ul>
        </div>
      )}

      {/* Footer */}
      <div className="mt-6 pt-4 border-t border-white/5">
        <p className="text-xs text-gray-500">
          <strong className="text-gray-400">SHAP values</strong> decompose each prediction
          into feature contributions. Positive values increase risk.
        </p>
      </div>
    </motion.div>
  );
}