import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import axios from 'axios';
import { AlertTriangle, CheckCircle, Filter, RefreshCw, Bell, BellOff, Zap } from 'lucide-react';
import AlertFeed from '../components/AlertFeed';
import LoadingSkeleton from '../components/LoadingSkeleton';
import ErrorFallback from '../components/ErrorFallback';
import AnimatedCounter from '../components/AnimatedCounter';

export default function Alerts() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<'active' | 'resolved' | 'all'>('active');
  const [typeFilter, setTypeFilter] = useState<string>('all');

  const API_URL = process.env.NEXT_PUBLIC_BACKEND_API || 'http://localhost:8001';

  const fetchAlerts = async () => {
    try {
      setError(null);
      const params: any = {};
      if (statusFilter !== 'all') params.status = statusFilter;

      const res = await axios.get(`${API_URL}/api/risk/alerts`, { params });
      setAlerts(res.data.alerts || []);
      setLoading(false);
    } catch (err: any) {
      setError(err.message || 'Failed to load alerts');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 15000);
    return () => clearInterval(interval);
  }, [statusFilter]);

  // Filter alerts by type
  const filteredAlerts = useMemo(() => {
    if (typeFilter === 'all') return alerts;
    return alerts.filter((a) => a.alert_type === typeFilter);
  }, [alerts, typeFilter]);

  // Stats
  const stats = useMemo(() => {
    const active = alerts.filter((a) => a.status === 'active').length;
    const highRisk = alerts.filter((a) => a.risk_level === 'HIGH').length;
    const today = alerts.filter(
      (a) => new Date(a.created_at).toDateString() === new Date().toDateString()
    ).length;
    const escalations = alerts.filter((a) => a.alert_type === 'RISK_ESCALATION_ALERT').length;
    const riskSpikes = alerts.filter((a) => a.alert_type === 'RISK_SPIKE').length;

    return { active, highRisk, today, escalations, riskSpikes };
  }, [alerts]);

  // Alert types for filter
  const alertTypes = [
    { value: 'all', label: 'All Types' },
    { value: 'HIGH_RISK_ALERT', label: 'High Risk' },
    { value: 'RISK_SPIKE', label: 'Risk Spike' },
    { value: 'EARLY_WARNING_ALERT', label: 'Early Warning' },
    { value: 'RISK_ESCALATION_ALERT', label: 'Escalation' },
  ];

  if (error) {
    return (
      <div className="container mx-auto px-4 py-12">
        <ErrorFallback error={error} onRetry={fetchAlerts} />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2 flex items-center gap-3">
            <AlertTriangle className="w-8 h-8 text-risk-medium" />
            Alert Center
          </h1>
          <p className="text-gray-400">Real-time risk alerts and escalation events</p>
        </div>
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={fetchAlerts}
          className="px-4 py-2 bg-dark-700 text-white rounded-lg flex items-center gap-2 border border-white/10 hover:border-defi-primary/50 transition-colors"
          data-testid="refresh-alerts"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </motion.button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-5"
        >
          <div className="flex items-center gap-2 mb-2">
            <Bell className="w-4 h-4 text-risk-high" />
            <span className="text-sm text-gray-400">Active Alerts</span>
          </div>
          <AnimatedCounter value={stats.active} className="text-2xl font-bold text-white" />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass-card p-5"
        >
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-4 h-4 text-risk-high" />
            <span className="text-sm text-gray-400">High Risk</span>
          </div>
          <AnimatedCounter value={stats.highRisk} className="text-2xl font-bold text-risk-high" />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="glass-card p-5"
          data-testid="risk-spikes-stat"
        >
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-4 h-4 text-defi-primary" />
            <span className="text-sm text-gray-400">Risk Spikes</span>
          </div>
          <AnimatedCounter value={stats.riskSpikes} className="text-2xl font-bold text-defi-primary" />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="glass-card p-5"
        >
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="w-4 h-4 text-risk-low" />
            <span className="text-sm text-gray-400">Today</span>
          </div>
          <AnimatedCounter value={stats.today} className="text-2xl font-bold text-white" />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="glass-card p-5"
        >
          <div className="flex items-center gap-2 mb-2">
            <Filter className="w-4 h-4 text-defi-secondary" />
            <span className="text-sm text-gray-400">Escalations</span>
          </div>
          <AnimatedCounter value={stats.escalations} className="text-2xl font-bold text-defi-secondary" />
        </motion.div>
      </div>

      {/* Filters */}
      <div className="glass-card p-4 mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Status Filter */}
          <div className="flex gap-2">
            <span className="text-sm text-gray-500 self-center mr-2">Status:</span>
            {(['active', 'resolved', 'all'] as const).map((status) => (
              <button
                key={status}
                onClick={() => setStatusFilter(status)}
                className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-all ${
                  statusFilter === status
                    ? 'bg-defi-primary text-white'
                    : 'bg-dark-700 text-gray-400 hover:text-white'
                }`}
                data-testid={`filter-status-${status}`}
              >
                {status === 'active' && <Bell className="w-3 h-3" />}
                {status === 'resolved' && <BellOff className="w-3 h-3" />}
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </button>
            ))}
          </div>

          {/* Type Filter */}
          <div className="flex gap-2 md:ml-auto flex-wrap">
            <span className="text-sm text-gray-500 self-center mr-2">Type:</span>
            {alertTypes.map((type) => (
              <button
                key={type.value}
                onClick={() => setTypeFilter(type.value)}
                className={`px-3 py-2 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
                  typeFilter === type.value
                    ? type.value === 'RISK_SPIKE' 
                      ? 'bg-defi-primary text-white shadow-glow-cyan' 
                      : 'bg-defi-secondary text-white'
                    : type.value === 'RISK_SPIKE'
                      ? 'bg-dark-700 text-defi-primary hover:bg-defi-primary/10 border border-defi-primary/30'
                      : 'bg-dark-700 text-gray-400 hover:text-white'
                }`}
                data-testid={`filter-type-${type.value}`}
              >
                {type.value === 'RISK_SPIKE' && <Zap className="w-3 h-3" />}
                {type.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Alert Feed */}
      {loading ? (
        <div className="space-y-4">
          <LoadingSkeleton type="card" count={5} />
        </div>
      ) : (
        <AlertFeed alerts={filteredAlerts} />
      )}
    </div>
  );
}