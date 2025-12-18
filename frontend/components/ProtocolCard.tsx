import Link from 'next/link';
import RiskBadge from './RiskBadge';
import RiskGauge from './RiskGauge';
import { formatDistanceToNow } from 'date-fns';
import { useState } from 'react';

interface ProtocolCardProps {
  pool_id: string;
  protocol: string;
  category: string;
  tvl: number;
  volume_24h: number;
  risk_score?: number;
  last_update: string;
  asset?: string;
  data_source?: string;
}

const categoryColors: Record<string, string> = {
  'DEX': 'bg-blue-500/20 text-blue-400',
  'Lending': 'bg-green-500/20 text-green-400',
  'Other': 'bg-gray-500/20 text-gray-400',
};

// Real protocol logo URLs from official/trusted sources
const protocolLogos: Record<string, string> = {
  'Uniswap V2': 'https://assets.coingecko.com/coins/images/12504/small/uniswap-uni.png',
  'Uniswap V3': 'https://assets.coingecko.com/coins/images/12504/small/uniswap-uni.png',
  'Aave V3': 'https://assets.coingecko.com/coins/images/12645/small/AAVE.png',
  'Compound V2': 'https://assets.coingecko.com/coins/images/10775/small/COMP.png',
  'Curve': 'https://assets.coingecko.com/coins/images/12124/small/Curve.png',
};

// Fallback emoji icons
const protocolEmojis: Record<string, string> = {
  'Uniswap V2': '🦄',
  'Uniswap V3': '🦄',
  'Aave V3': '👻',
  'Compound V2': '🏛️',
  'Curve': '🌀',
};

export default function ProtocolCard({
  pool_id,
  protocol,
  category,
  tvl,
  volume_24h,
  risk_score,
  last_update,
  asset,
  data_source
}: ProtocolCardProps) {
  const [imageError, setImageError] = useState(false);
  
  const formatCurrency = (value: number) => {
    if (value >= 1_000_000_000) {
      return `$${(value / 1_000_000_000).toFixed(2)}B`;
    } else if (value >= 1_000_000) {
      return `$${(value / 1_000_000).toFixed(2)}M`;
    } else if (value >= 1_000) {
      return `$${(value / 1_000).toFixed(2)}K`;
    }
    return `$${value.toFixed(2)}`;
  };

  // Extract display name from pool_id or asset prop
  const getDisplayName = () => {
    if (asset) return asset;
    // Parse pool_id like "uniswap_v2_usdc_eth" -> "USDC-ETH"
    const parts = pool_id.split('_');
    if (parts.length >= 3) {
      return parts.slice(2).join('-').toUpperCase();
    }
    return pool_id.toUpperCase();
  };

  const logoUrl = protocolLogos[protocol];
  const fallbackEmoji = protocolEmojis[protocol] || '📊';

  return (
    <Link
      href={`/pool/${encodeURIComponent(pool_id)}`}
      className="block"
    >
      <div
        className="bg-gray-800/50 backdrop-blur-sm rounded-lg border border-gray-700 p-6 hover:border-blue-500 transition-all hover:shadow-lg hover:shadow-blue-500/20 group"
        data-testid={`protocol-card-${pool_id}`}
      >
        {/* Header */}
        <div className="flex justify-between items-start mb-4">
          <div className="flex items-center gap-3">
            {/* Protocol Logo */}
            <div className="w-10 h-10 flex items-center justify-center">
              {logoUrl && !imageError ? (
                <img 
                  src={logoUrl} 
                  alt={protocol} 
                  className="w-10 h-10 rounded-full bg-white p-0.5"
                  onError={() => setImageError(true)}
                />
              ) : (
                <span className="text-3xl">{fallbackEmoji}</span>
              )}
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white group-hover:text-blue-400 transition-colors">
                {getDisplayName()}
              </h3>
              <div className="flex gap-2 mt-1 items-center">
                <span className="text-xs text-gray-400">{protocol}</span>
                <span className={`text-xs px-2 py-0.5 rounded ${categoryColors[category]}`}>
                  {category}
                </span>
                {data_source === 'live' && (
                  <span className="flex items-center gap-1 text-xs text-green-400">
                    <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse"></span>
                    Live
                  </span>
                )}
              </div>
            </div>
          </div>
          {risk_score !== undefined && <RiskBadge score={risk_score} />}
        </div>

        {/* Gauge Visualization */}
        {risk_score !== undefined && (
          <div className="py-4 flex justify-center bg-gradient-to-b from-gray-800/50 to-transparent rounded-lg mb-4">
            <RiskGauge score={risk_score} size={140} showLabel={false} />
          </div>
        )}

        {/* Metrics */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <div className="text-xs text-gray-400 mb-1">TVL</div>
            <div className="text-lg font-semibold text-white">{formatCurrency(tvl)}</div>
          </div>
          <div>
            <div className="text-xs text-gray-400 mb-1">24h Volume</div>
            <div className="text-lg font-semibold text-white">{formatCurrency(volume_24h)}</div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-between items-center pt-4 border-t border-gray-700">
          <span className="text-xs text-gray-400">
            Updated {formatDistanceToNow(new Date(last_update), { addSuffix: true })}
          </span>
          <span className="text-blue-400 text-sm group-hover:text-blue-300">→</span>
        </div>
      </div>
    </Link>
  );
}
