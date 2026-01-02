import { motion } from 'framer-motion';
import Link from 'next/link';
import { TrendingUp, TrendingDown, Minus, ExternalLink } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { useState, useEffect, useRef } from 'react';

interface ProtocolRiskCardProps {
  pool_id: string;
  protocol: string;
  category: string;
  tvl: number;
  volume_24h: number;
  risk_score?: number;
  risk_level?: string;
  trend?: 'up' | 'down' | 'stable';
  last_update: string;
  data_source?: string;
  index?: number;
}

const categoryIcons: Record<string, string> = {
  DEX: '🔄',
  Lending: '🏦',
  Yield: '🌱',
  Other: '📊',
};

const protocolEmojis: Record<string, string> = {
  'Uniswap V2': '🦄',
  'Uniswap V3': '🦄',
  'Aave V3': '👻',
  'Compound V2': '🏛️',
  Curve: '🌀',
};

export default function ProtocolRiskCard({
  pool_id,
  protocol,
  category,
  tvl,
  volume_24h,
  risk_score,
  risk_level,
  trend = 'stable',
  last_update,
  data_source,
  index = 0,
}: ProtocolRiskCardProps) {
  const [animatedScore, setAnimatedScore] = useState(0);
  const hasAnimated = useRef(false);

  useEffect(() => {
    if (risk_score !== undefined && !hasAnimated.current) {
      hasAnimated.current = true;
      const duration = 1000;
      const startTime = Date.now();

      const animate = () => {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        setAnimatedScore(eased * risk_score);

        if (progress < 1) {
          requestAnimationFrame(animate);
        }
      };

      requestAnimationFrame(animate);
    }
  }, [risk_score]);

  const formatCurrency = (value: number) => {
    if (value >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(2)}B`;
    if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
    if (value >= 1_000) return `$${(value / 1_000).toFixed(2)}K`;
    return `$${value.toFixed(2)}`;
  };

  const getDisplayName = () => {
    const parts = pool_id.split('_');
    if (parts.length >= 3) {
      return parts.slice(2).join('-').toUpperCase();
    }
    return pool_id.toUpperCase();
  };

  const getRiskConfig = (score: number) => {
    if (score < 30)
      return {
        level: 'LOW',
        color: 'text-risk-low',
        bg: 'bg-risk-low/10',
        border: 'border-risk-low/30',
        glow: 'group-hover:shadow-glow-green',
      };
    if (score < 65)
      return {
        level: 'MEDIUM',
        color: 'text-risk-medium',
        bg: 'bg-risk-medium/10',
        border: 'border-risk-medium/30',
        glow: 'group-hover:shadow-glow-yellow',
      };
    return {
      level: 'HIGH',
      color: 'text-risk-high',
      bg: 'bg-risk-high/10',
      border: 'border-risk-high/30',
      glow: 'group-hover:shadow-glow-red',
    };
  };

  const riskConfig = risk_score !== undefined ? getRiskConfig(risk_score) : null;

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  const trendColor = trend === 'up' ? 'text-risk-high' : trend === 'down' ? 'text-risk-low' : 'text-gray-400';

  return (
    <Link href={`/protocols/${encodeURIComponent(pool_id)}`}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: index * 0.05 }}
        whileHover={{ y: -4, transition: { duration: 0.2 } }}
        className={`group glass-card p-5 cursor-pointer transition-all duration-300 ${
          riskConfig ? `hover:${riskConfig.border} ${riskConfig.glow}` : 'hover:border-defi-primary/30 hover:shadow-glow-cyan'
        }`}
        data-testid={`protocol-card-${pool_id}`}
      >
        {/* Header */}
        <div className="flex justify-between items-start mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-dark-600 flex items-center justify-center text-2xl">
              {protocolEmojis[protocol] || categoryIcons[category] || '📊'}
            </div>
            <div>
              <h3 className="text-base font-semibold text-white group-hover:text-defi-primary transition-colors">
                {getDisplayName()}
              </h3>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-xs text-gray-500">{protocol}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-dark-600 text-gray-400">
                  {category}
                </span>
              </div>
            </div>
          </div>

          {/* Risk Badge */}
          {riskConfig && (
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: index * 0.05 + 0.3 }}
              className={`px-2.5 py-1 rounded-full ${riskConfig.bg} ${riskConfig.border} border flex items-center gap-1.5`}
            >
              <div className={`w-1.5 h-1.5 rounded-full ${riskConfig.color.replace('text-', 'bg-')} animate-pulse`} />
              <span className={`text-xs font-bold ${riskConfig.color}`}>
                {risk_level || riskConfig.level}
              </span>
            </motion.div>
          )}
        </div>

        {/* Risk Score Display */}
        {risk_score !== undefined && (
          <div className="mb-4 p-4 rounded-lg bg-dark-800/50 border border-white/5">
            <div className="flex items-end justify-between">
              <div>
                <div className="text-xs text-gray-500 mb-1">Risk Score</div>
                <div className={`text-3xl font-bold ${riskConfig?.color}`}>
                  {animatedScore.toFixed(1)}
                  <span className="text-sm text-gray-500 font-normal">/100</span>
                </div>
              </div>
              <div className={`flex items-center gap-1 ${trendColor}`}>
                <TrendIcon className="w-4 h-4" />
                <span className="text-xs font-medium">
                  {trend === 'up' ? 'Rising' : trend === 'down' ? 'Falling' : 'Stable'}
                </span>
              </div>
            </div>

            {/* Mini progress bar */}
            <div className="mt-3 h-1.5 bg-dark-600 rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${Math.min(animatedScore, 100)}%` }}
                transition={{ duration: 1, delay: index * 0.05 }}
                className={`h-full rounded-full ${
                  risk_score < 30
                    ? 'bg-gradient-to-r from-risk-low/50 to-risk-low'
                    : risk_score < 65
                    ? 'bg-gradient-to-r from-risk-medium/50 to-risk-medium'
                    : 'bg-gradient-to-r from-risk-high/50 to-risk-high'
                }`}
              />
            </div>
          </div>
        )}

        {/* Metrics */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="p-2.5 rounded-lg bg-dark-800/30">
            <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-0.5">TVL</div>
            <div className="text-sm font-semibold text-white">{formatCurrency(tvl)}</div>
          </div>
          <div className="p-2.5 rounded-lg bg-dark-800/30">
            <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-0.5">24h Volume</div>
            <div className="text-sm font-semibold text-white">{formatCurrency(volume_24h)}</div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-white/5">
          <div className="flex items-center gap-2">
            {data_source === 'live' && (
              <span className="flex items-center gap-1 text-[10px] text-risk-low">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-risk-low opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-risk-low" />
                </span>
                Live
              </span>
            )}
            <span className="text-[10px] text-gray-500">
              {formatDistanceToNow(new Date(last_update), { addSuffix: true })}
            </span>
          </div>
          <span className="text-defi-primary text-sm opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1">
            View <ExternalLink className="w-3 h-3" />
          </span>
        </div>
      </motion.div>
    </Link>
  );
}
