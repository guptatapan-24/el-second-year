import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Info, TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface FeatureTooltipProps {
  feature: string;
  value?: number | string;
  children?: React.ReactNode;
}

const FEATURE_INFO: Record<string, {
  name: string;
  description: string;
  unit: string;
  riskDirection: string;
  icon: 'up' | 'down' | 'neutral';
}> = {
  tvl: {
    name: 'Total Value Locked (TVL)',
    description: 'Total amount of assets deposited in the protocol. A drop in TVL can indicate users withdrawing funds due to concerns.',
    unit: 'USD',
    riskDirection: 'Lower or rapid decrease = Higher Risk',
    icon: 'down'
  },
  tvl_change_6h: {
    name: 'TVL Change (6h)',
    description: 'Percentage change in TVL over the past 6 hours. Sharp declines often precede larger crashes.',
    unit: '%',
    riskDirection: 'Negative values = Higher Risk',
    icon: 'down'
  },
  tvl_change_24h: {
    name: 'TVL Change (24h)',
    description: 'Percentage change in TVL over the past 24 hours. Sustained outflows indicate deteriorating confidence.',
    unit: '%',
    riskDirection: 'Negative values = Higher Risk',
    icon: 'down'
  },
  tvl_acceleration: {
    name: 'TVL Acceleration',
    description: 'Rate of change of TVL change (second derivative). Accelerating outflows suggest panic selling.',
    unit: 'Rate',
    riskDirection: 'Negative values = Higher Risk',
    icon: 'down'
  },
  volume_24h: {
    name: '24h Trading Volume',
    description: 'Total trading volume in the past 24 hours. Unusual spikes may indicate panic or manipulation.',
    unit: 'USD',
    riskDirection: 'Abnormal spikes = Higher Risk',
    icon: 'up'
  },
  volume_spike_ratio: {
    name: 'Volume Spike Ratio',
    description: 'Current volume compared to the rolling average. Values >2 indicate unusual trading activity.',
    unit: 'Ratio',
    riskDirection: 'Values >2 = Higher Risk',
    icon: 'up'
  },
  reserve_imbalance: {
    name: 'Reserve Imbalance',
    description: 'The imbalance between reserve0 and reserve1 in a liquidity pool. High imbalance indicates one-sided pressure.',
    unit: '0-1',
    riskDirection: 'Higher values = Higher Risk',
    icon: 'up'
  },
  reserve_imbalance_rate: {
    name: 'Reserve Imbalance Rate',
    description: 'Rate of change of reserve imbalance. Rapidly increasing imbalance suggests impending depeg or liquidity crisis.',
    unit: 'Rate',
    riskDirection: 'Positive values = Higher Risk',
    icon: 'up'
  },
  volatility_6h: {
    name: 'Short-term Volatility (6h)',
    description: 'Standard deviation of TVL returns over 6 hours. Higher volatility indicates market stress.',
    unit: 'Std Dev',
    riskDirection: 'Higher values = Higher Risk',
    icon: 'up'
  },
  volatility_24h: {
    name: 'Long-term Volatility (24h)',
    description: 'Standard deviation of TVL returns over 24 hours. Baseline measure of protocol stability.',
    unit: 'Std Dev',
    riskDirection: 'Higher values = Higher Risk',
    icon: 'up'
  },
  volatility_ratio: {
    name: 'Volatility Ratio',
    description: 'Ratio of short-term to long-term volatility. Values >1.5 indicate regime change or emerging crisis.',
    unit: 'Ratio',
    riskDirection: 'Values >1.5 = Higher Risk',
    icon: 'up'
  },
  early_warning_score: {
    name: 'Early Warning Score',
    description: 'Composite signal combining all risk factors. Designed to detect patterns that precede crashes.',
    unit: '0-100',
    riskDirection: 'Higher values = Higher Risk',
    icon: 'up'
  }
};

export default function FeatureTooltip({ feature, value, children }: FeatureTooltipProps) {
  const [isOpen, setIsOpen] = useState(false);
  const info = FEATURE_INFO[feature] || {
    name: feature.replace(/_/g, ' '),
    description: 'Feature used in risk calculation',
    unit: '-',
    riskDirection: 'Context-dependent',
    icon: 'neutral'
  };

  const IconComponent = info.icon === 'up' ? TrendingUp : info.icon === 'down' ? TrendingDown : Minus;
  const iconColor = info.icon === 'up' ? 'text-risk-high' : info.icon === 'down' ? 'text-risk-low' : 'text-gray-400';

  return (
    <div 
      className="relative inline-block"
      onMouseEnter={() => setIsOpen(true)}
      onMouseLeave={() => setIsOpen(false)}
    >
      {children || (
        <span className="flex items-center gap-1 cursor-help text-gray-300 hover:text-white transition-colors">
          {feature.replace(/_/g, ' ')}
          <Info className="w-3 h-3 text-gray-500" />
        </span>
      )}

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 5, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 5, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="
              absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2
              w-72 p-4 rounded-xl
              bg-dark-700/95 backdrop-blur-lg
              border border-white/10
              shadow-xl shadow-black/20
            "
            data-testid="feature-tooltip"
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
              <div>
                <h4 className="text-sm font-semibold text-white">{info.name}</h4>
                <span className="text-[10px] text-gray-500 font-mono">Unit: {info.unit}</span>
              </div>
              <IconComponent className={`w-4 h-4 ${iconColor}`} />
            </div>

            {/* Description */}
            <p className="text-xs text-gray-300 leading-relaxed mb-3">
              {info.description}
            </p>

            {/* Risk Direction */}
            <div className="pt-3 border-t border-white/10">
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-gray-500">Risk Impact:</span>
                <span className={`text-[10px] font-medium ${iconColor}`}>
                  {info.riskDirection}
                </span>
              </div>
            </div>

            {/* Current Value if provided */}
            {value !== undefined && (
              <div className="mt-3 pt-3 border-t border-white/10">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-gray-500">Current Value:</span>
                  <span className="text-sm font-mono font-bold text-white">
                    {typeof value === 'number' ? value.toFixed(4) : value}
                  </span>
                </div>
              </div>
            )}

            {/* Arrow */}
            <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-px">
              <div className="border-8 border-transparent border-t-dark-700/95" />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}