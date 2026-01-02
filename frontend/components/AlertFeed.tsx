import { motion } from 'framer-motion';
import { AlertTriangle, AlertCircle, TrendingUp, Clock, CheckCircle, XCircle } from 'lucide-react';
import { formatDistanceToNow, format } from 'date-fns';

interface Alert {
  id: number;
  pool_id: string;
  alert_type: string;
  risk_score: number;
  risk_level: string;
  message: string;
  top_reasons?: Array<{ feature: string; impact: number }>;
  status: string;
  previous_risk_level?: string;
  previous_risk_score?: number;
  created_at: string;
}

interface AlertFeedProps {
  alerts: Alert[];
  loading?: boolean;
  compact?: boolean;
}

const alertTypeConfig: Record<string, { icon: any; color: string; bg: string }> = {
  HIGH_RISK_ALERT: {
    icon: AlertTriangle,
    color: 'text-risk-high',
    bg: 'bg-risk-high/10 border-risk-high/30',
  },
  EARLY_WARNING_ALERT: {
    icon: AlertCircle,
    color: 'text-risk-medium',
    bg: 'bg-risk-medium/10 border-risk-medium/30',
  },
  RISK_ESCALATION_ALERT: {
    icon: TrendingUp,
    color: 'text-defi-secondary',
    bg: 'bg-defi-secondary/10 border-defi-secondary/30',
  },
};

export default function AlertFeed({ alerts, loading, compact }: AlertFeedProps) {
  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="glass-card p-4">
            <div className="flex gap-4">
              <div className="w-10 h-10 rounded-lg bg-dark-600 shimmer-loading" />
              <div className="flex-1 space-y-2">
                <div className="h-4 w-32 bg-dark-600 rounded shimmer-loading" />
                <div className="h-3 w-full bg-dark-600 rounded shimmer-loading" />
                <div className="h-3 w-2/3 bg-dark-600 rounded shimmer-loading" />
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (alerts.length === 0) {
    return (
      <div className="glass-card p-8 text-center">
        <CheckCircle className="w-12 h-12 text-risk-low mx-auto mb-3" />
        <h3 className="text-lg font-semibold text-white mb-1">All Clear</h3>
        <p className="text-gray-400 text-sm">No active alerts at this time</p>
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="alert-feed">
      {alerts.map((alert, idx) => {
        const config = alertTypeConfig[alert.alert_type] || alertTypeConfig.HIGH_RISK_ALERT;
        const Icon = config.icon;
        const isNew = Date.now() - new Date(alert.created_at).getTime() < 300000; // 5 minutes

        return (
          <motion.div
            key={alert.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.05 }}
            className={`glass-card border overflow-hidden ${config.bg} ${
              isNew ? 'animate-pulse-slow' : ''
            }`}
            data-testid={`alert-${alert.id}`}
          >
            {/* Severity strip */}
            <div
              className={`h-1 ${
                alert.risk_level === 'HIGH'
                  ? 'bg-risk-high'
                  : alert.risk_level === 'MEDIUM'
                  ? 'bg-risk-medium'
                  : 'bg-risk-low'
              }`}
            />

            <div className={`p-4 ${compact ? '' : 'md:p-5'}`}>
              <div className="flex gap-4">
                {/* Icon */}
                <div
                  className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                    config.bg.split(' ')[0]
                  }`}
                >
                  <Icon className={`w-5 h-5 ${config.color}`} />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="text-sm font-semibold text-white">{alert.pool_id}</h4>
                        {isNew && (
                          <span className="px-1.5 py-0.5 text-[10px] font-bold rounded bg-risk-high text-white">
                            NEW
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className={`text-xs font-medium ${config.color}`}>
                          {alert.alert_type.replace(/_/g, ' ')}
                        </span>
                        <span className="text-gray-600">•</span>
                        <span className="text-xs text-gray-500 flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatDistanceToNow(new Date(alert.created_at), { addSuffix: true })}
                        </span>
                      </div>
                    </div>

                    {/* Risk Score */}
                    <div className="text-right flex-shrink-0">
                      <div
                        className={`text-xl font-bold ${
                          alert.risk_level === 'HIGH'
                            ? 'text-risk-high'
                            : alert.risk_level === 'MEDIUM'
                            ? 'text-risk-medium'
                            : 'text-risk-low'
                        }`}
                      >
                        {alert.risk_score.toFixed(1)}
                      </div>
                      <div className="text-[10px] text-gray-500">Risk Score</div>
                    </div>
                  </div>

                  {/* Message */}
                  <p className="text-sm text-gray-300 mb-3">{alert.message}</p>

                  {/* Previous state (if escalation) */}
                  {alert.previous_risk_score !== undefined && (
                    <div className="flex items-center gap-2 text-xs text-gray-500 mb-3">
                      <span>Previous:</span>
                      <span
                        className={`font-medium ${
                          alert.previous_risk_level === 'HIGH'
                            ? 'text-risk-high'
                            : alert.previous_risk_level === 'MEDIUM'
                            ? 'text-risk-medium'
                            : 'text-risk-low'
                        }`}
                      >
                        {alert.previous_risk_level} ({alert.previous_risk_score?.toFixed(1)})
                      </span>
                      <span>→</span>
                      <span
                        className={`font-medium ${
                          alert.risk_level === 'HIGH'
                            ? 'text-risk-high'
                            : alert.risk_level === 'MEDIUM'
                            ? 'text-risk-medium'
                            : 'text-risk-low'
                        }`}
                      >
                        {alert.risk_level} ({alert.risk_score.toFixed(1)})
                      </span>
                    </div>
                  )}

                  {/* Top reasons (if not compact) */}
                  {!compact && alert.top_reasons && alert.top_reasons.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {alert.top_reasons.slice(0, 3).map((reason, i) => (
                        <span
                          key={i}
                          className="px-2 py-1 text-[10px] rounded bg-dark-700 text-gray-400 border border-white/5"
                        >
                          {reason.feature.replace(/_/g, ' ')}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Status */}
                  <div className="flex items-center justify-between mt-3 pt-3 border-t border-white/5">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium ${
                        alert.status === 'active'
                          ? 'bg-risk-high/10 text-risk-high'
                          : 'bg-gray-700 text-gray-400'
                      }`}
                    >
                      {alert.status === 'active' ? (
                        <span className="relative flex h-1.5 w-1.5">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-risk-high opacity-75" />
                          <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-risk-high" />
                        </span>
                      ) : (
                        <XCircle className="w-3 h-3" />
                      )}
                      {alert.status.toUpperCase()}
                    </span>
                    <span className="text-[10px] text-gray-600">
                      {format(new Date(alert.created_at), 'PPpp')}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
