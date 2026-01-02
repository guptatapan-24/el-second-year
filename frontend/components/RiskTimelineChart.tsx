import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Area, AreaChart } from 'recharts';
import { motion } from 'framer-motion';
import { format } from 'date-fns';

interface TimelineData {
  timestamp: string;
  risk_score: number;
  risk_level: string;
  has_alert?: boolean;
}

interface RiskTimelineChartProps {
  data: TimelineData[];
  loading?: boolean;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload || !payload[0]) return null;

  const data = payload[0].payload;
  const riskColor = data.risk_score < 30 ? '#22c55e' : data.risk_score < 65 ? '#f59e0b' : '#ef4444';

  return (
    <div className="glass-card p-3 border border-white/10">
      <div className="text-xs text-gray-400 mb-1">
        {format(new Date(data.timestamp), 'PPpp')}
      </div>
      <div className="flex items-center gap-2">
        <span className="text-2xl font-bold" style={{ color: riskColor }}>
          {data.risk_score.toFixed(1)}
        </span>
        <span
          className="text-xs px-2 py-0.5 rounded-full font-medium"
          style={{ backgroundColor: `${riskColor}20`, color: riskColor }}
        >
          {data.risk_level}
        </span>
      </div>
      {data.has_alert && (
        <div className="mt-2 text-xs text-risk-high flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-risk-high animate-pulse" />
          Alert triggered
        </div>
      )}
    </div>
  );
};

export default function RiskTimelineChart({ data, loading }: RiskTimelineChartProps) {
  if (loading) {
    return (
      <div className="glass-card p-6">
        <div className="h-5 w-40 bg-dark-600 rounded shimmer-loading mb-4" />
        <div className="h-64 w-full bg-dark-600 rounded-lg shimmer-loading" />
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="glass-card p-6 text-center">
        <p className="text-gray-400">No timeline data available</p>
      </div>
    );
  }

  const chartData = data.map((d) => ({
    ...d,
    time: format(new Date(d.timestamp), 'HH:mm'),
    date: format(new Date(d.timestamp), 'MMM dd'),
  }));

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-6"
      data-testid="risk-timeline"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Risk Score Timeline</h3>
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-full bg-risk-low" />
            <span className="text-gray-400">Low</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-full bg-risk-medium" />
            <span className="text-gray-400">Medium</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-full bg-risk-high" />
            <span className="text-gray-400">High</span>
          </div>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="riskGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#06b6d4" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#06b6d4" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis
            dataKey="time"
            stroke="#6b7280"
            tick={{ fill: '#6b7280', fontSize: 11 }}
            axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
          />
          <YAxis
            domain={[0, 100]}
            stroke="#6b7280"
            tick={{ fill: '#6b7280', fontSize: 11 }}
            axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
          />
          <Tooltip content={<CustomTooltip />} />

          {/* Reference lines for risk thresholds */}
          <ReferenceLine y={30} stroke="#22c55e" strokeDasharray="5 5" strokeOpacity={0.5} />
          <ReferenceLine y={65} stroke="#f59e0b" strokeDasharray="5 5" strokeOpacity={0.5} />

          <Area
            type="monotone"
            dataKey="risk_score"
            stroke="#06b6d4"
            strokeWidth={2}
            fill="url(#riskGradient)"
            dot={(props: any) => {
              const { cx, cy, payload } = props;
              if (!payload.has_alert) return null;
              return (
                <circle
                  cx={cx}
                  cy={cy}
                  r={6}
                  fill="#ef4444"
                  stroke="#fff"
                  strokeWidth={2}
                  className="animate-pulse"
                />
              );
            }}
          />
        </AreaChart>
      </ResponsiveContainer>

      <div className="mt-4 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>{chartData.length} data points</span>
          <span>Red dots indicate alert triggers</span>
        </div>
      </div>
    </motion.div>
  );
}
