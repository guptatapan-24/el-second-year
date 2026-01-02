import { motion } from 'framer-motion';
import { Activity, DollarSign, TrendingUp, AlertTriangle, Shield, Zap } from 'lucide-react';
import AnimatedCounter from './AnimatedCounter';

interface StatCardProps {
  title: string;
  value: number;
  prefix?: string;
  suffix?: string;
  icon: any;
  color: string;
  change?: number;
  index?: number;
}

function StatCard({ title, value, prefix = '', suffix = '', icon: Icon, color, change, index = 0 }: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className={`glass-card p-5 relative overflow-hidden group hover:border-${color}/30 transition-all`}
    >
      {/* Background glow */}
      <div className={`absolute top-0 right-0 w-24 h-24 bg-${color}/5 rounded-full blur-2xl group-hover:bg-${color}/10 transition-all`} />
      
      <div className="relative">
        <div className="flex items-center justify-between mb-3">
          <span className="text-gray-400 text-sm">{title}</span>
          <div className={`w-8 h-8 rounded-lg bg-${color}/10 flex items-center justify-center`}>
            <Icon className={`w-4 h-4 text-${color}`} />
          </div>
        </div>
        
        <div className="flex items-end gap-2">
          <AnimatedCounter
            value={value}
            prefix={prefix}
            className={`text-2xl font-bold text-white`}
          />
          {suffix && <span className="text-gray-500 text-sm mb-0.5">{suffix}</span>}
        </div>

        {change !== undefined && (
          <div className={`mt-2 text-xs font-medium ${
            change >= 0 ? 'text-risk-low' : 'text-risk-high'
          }`}>
            {change >= 0 ? '↑' : '↓'} {Math.abs(change).toFixed(1)}% from last hour
          </div>
        )}
      </div>
    </motion.div>
  );
}

interface GlobalStatsProps {
  totalProtocols: number;
  highRiskCount: number;
  alertsToday: number;
  totalTVL: number;
  avgRisk: number;
  loading?: boolean;
}

export default function GlobalStats({
  totalProtocols,
  highRiskCount,
  alertsToday,
  totalTVL,
  avgRisk,
  loading,
}: GlobalStatsProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="glass-card p-5">
            <div className="h-4 w-24 bg-dark-600 rounded shimmer-loading mb-3" />
            <div className="h-8 w-20 bg-dark-600 rounded shimmer-loading" />
          </div>
        ))}
      </div>
    );
  }

  const stats = [
    {
      title: 'Monitored Protocols',
      value: totalProtocols,
      icon: Shield,
      color: 'defi-primary',
    },
    {
      title: 'Total TVL',
      value: totalTVL,
      prefix: '$',
      icon: DollarSign,
      color: 'risk-low',
    },
    {
      title: 'Avg Risk Score',
      value: avgRisk,
      suffix: '/100',
      icon: Activity,
      color: avgRisk < 30 ? 'risk-low' : avgRisk < 65 ? 'risk-medium' : 'risk-high',
    },
    {
      title: 'High Risk Protocols',
      value: highRiskCount,
      icon: AlertTriangle,
      color: 'risk-high',
    },
    {
      title: 'Alerts Today',
      value: alertsToday,
      icon: Zap,
      color: alertsToday > 0 ? 'risk-medium' : 'gray-400',
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4" data-testid="global-stats">
      {stats.map((stat, i) => (
        <StatCard key={stat.title} {...stat} index={i} />
      ))}
    </div>
  );
}
