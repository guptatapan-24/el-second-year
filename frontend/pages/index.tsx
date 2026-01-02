import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import axios from 'axios';
import { Shield, ChevronRight, Zap, Activity, TrendingUp, AlertTriangle } from 'lucide-react';
import GlobalStats from '../components/GlobalStats';
import AlertFeed from '../components/AlertFeed';
import LoadingSkeleton from '../components/LoadingSkeleton';
import ErrorFallback from '../components/ErrorFallback';

export default function Home() {
  const [summary, setSummary] = useState<any>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_BACKEND_API || 'http://localhost:8001';

  const fetchData = async () => {
    try {
      setError(null);
      const [summaryRes, alertsRes, healthRes] = await Promise.all([
        axios.get(`${API_URL}/api/risk/summary`),
        axios.get(`${API_URL}/api/risk/alerts?status=active`),
        axios.get(`${API_URL}/health`),
      ]);
      setSummary(summaryRes.data);
      setAlerts(alertsRes.data.alerts || []);
      setHealth(healthRes.data);
      setLoading(false);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard data');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (error) {
    return (
      <div className="container mx-auto px-4 py-12">
        <ErrorFallback error={error} onRetry={fetchData} />
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        {/* Animated background elements */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute top-20 left-10 w-72 h-72 bg-defi-primary/10 rounded-full blur-3xl animate-pulse-slow" />
          <div className="absolute bottom-20 right-10 w-96 h-96 bg-defi-secondary/10 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }} />
        </div>

        <div className="container mx-auto px-4 py-16 relative">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-center max-w-4xl mx-auto"
          >
            {/* Badge */}
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2 }}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-defi-primary/10 border border-defi-primary/30 text-defi-primary text-sm font-medium mb-6"
            >
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-defi-primary opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-defi-primary" />
              </span>
              AI-Powered Risk Monitoring
            </motion.div>

            {/* Title */}
            <h1 className="text-4xl md:text-6xl font-bold text-white mb-6">
              <span className="neon-text-cyan">VeriRisk</span>{' '}
              <span className="text-gray-400">Oracle</span>
            </h1>
            <p className="text-xl text-gray-400 mb-8 max-w-2xl mx-auto">
              Verifiable AI Risk Prediction for DeFi Protocols.
              <br />
              <span className="text-gray-500">XGBoost ML + SHAP Explainability + On-Chain Verification</span>
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-wrap justify-center gap-4 mb-12">
              <Link href="/protocols">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="px-8 py-3 bg-gradient-to-r from-defi-primary to-defi-secondary text-white font-semibold rounded-lg flex items-center gap-2 shadow-glow-cyan"
                  data-testid="view-protocols-btn"
                >
                  <Shield className="w-5 h-5" />
                  View Protocols
                  <ChevronRight className="w-4 h-4" />
                </motion.button>
              </Link>
              <Link href="/simulation">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="px-8 py-3 bg-dark-700 text-white font-semibold rounded-lg flex items-center gap-2 border border-white/10 hover:border-defi-secondary/50 transition-colors"
                  data-testid="simulation-btn"
                >
                  <Zap className="w-5 h-5" />
                  Try Simulation
                </motion.button>
              </Link>
            </div>

            {/* System Status */}
            {health && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4 }}
                className="inline-flex items-center gap-4 px-6 py-3 rounded-xl glass-card"
                data-testid="system-status"
              >
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${health.components?.model_server ? 'bg-risk-low' : 'bg-risk-high'}`} />
                  <span className="text-xs text-gray-400">ML Model</span>
                </div>
                <div className="w-px h-4 bg-white/10" />
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${health.components?.scheduler ? 'bg-risk-low' : 'bg-risk-high'}`} />
                  <span className="text-xs text-gray-400">Scheduler</span>
                </div>
                <div className="w-px h-4 bg-white/10" />
                <div className="flex items-center gap-2">
                  <Activity className="w-3 h-3 text-risk-low" />
                  <span className="text-xs text-gray-400">
                    {health.data_status?.recent_snapshots?.live_percentage || 0}% Live Data
                  </span>
                </div>
              </motion.div>
            )}
          </motion.div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="container mx-auto px-4 py-8">
        <GlobalStats
          totalProtocols={summary?.total_pools || 0}
          highRiskCount={summary?.high_risk_pools || 0}
          alertsToday={alerts.length}
          totalTVL={summary?.pools?.reduce((sum: number, p: any) => sum + (p.tvl || 0), 0) || 0}
          avgRisk={
            summary?.pools?.length > 0
              ? summary.pools.reduce((sum: number, p: any) => sum + p.latest_risk_score, 0) / summary.pools.length
              : 0
          }
          loading={loading}
        />
      </section>

      {/* Content Grid */}
      <section className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Risk Overview */}
          <div className="lg:col-span-2">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="glass-card p-6"
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-white flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-defi-primary" />
                  Protocol Risk Overview
                </h2>
                <Link href="/protocols" className="text-defi-primary text-sm hover:underline">
                  View All →
                </Link>
              </div>

              {loading ? (
                <div className="space-y-4">
                  <LoadingSkeleton type="text" count={5} />
                </div>
              ) : summary?.pools?.length > 0 ? (
                <div className="space-y-3">
                  {summary.pools.slice(0, 6).map((pool: any, idx: number) => {
                    const riskColor =
                      pool.latest_risk_score < 30
                        ? 'bg-risk-low'
                        : pool.latest_risk_score < 65
                        ? 'bg-risk-medium'
                        : 'bg-risk-high';
                    return (
                      <motion.div
                        key={pool.pool_id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: idx * 0.05 }}
                      >
                        <Link href={`/protocols/${encodeURIComponent(pool.pool_id)}`}>
                          <div className="flex items-center justify-between p-3 rounded-lg bg-dark-800/50 hover:bg-dark-700/50 transition-colors cursor-pointer border border-white/5 hover:border-defi-primary/30">
                            <div className="flex items-center gap-3">
                              <div className={`w-2 h-8 rounded-full ${riskColor}`} />
                              <div>
                                <div className="text-sm font-medium text-white">{pool.pool_id}</div>
                                <div className="text-xs text-gray-500">{pool.latest_risk_level}</div>
                              </div>
                            </div>
                            <div className="text-right">
                              <div
                                className={`text-lg font-bold ${
                                  pool.latest_risk_score < 30
                                    ? 'text-risk-low'
                                    : pool.latest_risk_score < 65
                                    ? 'text-risk-medium'
                                    : 'text-risk-high'
                                }`}
                              >
                                {pool.latest_risk_score.toFixed(1)}
                              </div>
                              {pool.active_alerts > 0 && (
                                <div className="text-[10px] text-risk-high flex items-center gap-1 justify-end">
                                  <AlertTriangle className="w-3 h-3" />
                                  {pool.active_alerts} alert{pool.active_alerts > 1 ? 's' : ''}
                                </div>
                              )}
                            </div>
                          </div>
                        </Link>
                      </motion.div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-400">
                  No protocols monitored yet
                </div>
              )}
            </motion.div>
          </div>

          {/* Recent Alerts */}
          <div>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="glass-card p-6"
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-white flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-risk-high" />
                  Recent Alerts
                </h2>
                <Link href="/alerts" className="text-defi-primary text-sm hover:underline">
                  View All →
                </Link>
              </div>

              <AlertFeed alerts={alerts.slice(0, 3)} loading={loading} compact />
            </motion.div>
          </div>
        </div>
      </section>

      {/* Quick Actions */}
      <section className="container mx-auto px-4 py-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6"
        >
          <Link href="/protocols">
            <div className="glass-card p-6 cursor-pointer hover:border-defi-primary/30 transition-all group">
              <Shield className="w-10 h-10 text-defi-primary mb-4 group-hover:scale-110 transition-transform" />
              <h3 className="text-lg font-semibold text-white mb-2">Protocol Dashboard</h3>
              <p className="text-sm text-gray-400">View all monitored protocols with ML-driven risk scores</p>
            </div>
          </Link>
          <Link href="/alerts">
            <div className="glass-card p-6 cursor-pointer hover:border-risk-medium/30 transition-all group">
              <AlertTriangle className="w-10 h-10 text-risk-medium mb-4 group-hover:scale-110 transition-transform" />
              <h3 className="text-lg font-semibold text-white mb-2">Alert Center</h3>
              <p className="text-sm text-gray-400">Monitor real-time alerts and escalation events</p>
            </div>
          </Link>
          <Link href="/simulation">
            <div className="glass-card p-6 cursor-pointer hover:border-defi-secondary/30 transition-all group">
              <Zap className="w-10 h-10 text-defi-secondary mb-4 group-hover:scale-110 transition-transform" />
              <h3 className="text-lg font-semibold text-white mb-2">Simulation Mode</h3>
              <p className="text-sm text-gray-400">Test system reactions to simulated crisis events</p>
            </div>
          </Link>
        </motion.div>
      </section>
    </div>
  );
}
