interface StatsOverviewProps {
  totalProtocols: number;
  totalTVL: number;
  totalVolume: number;
  avgRisk: number;
}

export default function StatsOverview({
  totalProtocols,
  totalTVL,
  totalVolume,
  avgRisk
}: StatsOverviewProps) {
  const formatCurrency = (value: number) => {
    if (value >= 1_000_000_000) {
      return `$${(value / 1_000_000_000).toFixed(2)}B`;
    } else if (value >= 1_000_000) {
      return `$${(value / 1_000_000).toFixed(2)}M`;
    }
    return `$${value.toFixed(2)}`;
  };

  const getRiskColor = (risk: number) => {
    if (risk < 30) return 'text-green-400';
    if (risk < 65) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
      <div className="bg-gradient-to-br from-blue-500/10 to-blue-600/10 backdrop-blur-sm rounded-lg border border-blue-500/30 p-6">
        <div className="text-blue-400 text-sm font-medium mb-2">Monitored Protocols</div>
        <div className="text-3xl font-bold text-white" data-testid="stat-protocols">{totalProtocols}</div>
      </div>

      <div className="bg-gradient-to-br from-green-500/10 to-green-600/10 backdrop-blur-sm rounded-lg border border-green-500/30 p-6">
        <div className="text-green-400 text-sm font-medium mb-2">Total TVL</div>
        <div className="text-3xl font-bold text-white" data-testid="stat-tvl">{formatCurrency(totalTVL)}</div>
      </div>

      <div className="bg-gradient-to-br from-purple-500/10 to-purple-600/10 backdrop-blur-sm rounded-lg border border-purple-500/30 p-6">
        <div className="text-purple-400 text-sm font-medium mb-2">24h Volume</div>
        <div className="text-3xl font-bold text-white" data-testid="stat-volume">{formatCurrency(totalVolume)}</div>
      </div>

      <div className="bg-gradient-to-br from-orange-500/10 to-orange-600/10 backdrop-blur-sm rounded-lg border border-orange-500/30 p-6">
        <div className="text-orange-400 text-sm font-medium mb-2">Avg Risk Score</div>
        <div className={`text-3xl font-bold ${getRiskColor(avgRisk)}`} data-testid="stat-risk">
          {avgRisk.toFixed(1)}
        </div>
      </div>
    </div>
  );
}
