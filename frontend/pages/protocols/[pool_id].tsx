import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { motion } from 'framer-motion';
import Link from 'next/link';
import axios from 'axios';
import { ArrowLeft, ExternalLink, RefreshCw, Clock, AlertTriangle } from 'lucide-react';
import RiskGaugeAnimated from '../../components/RiskGaugeAnimated';
import SHAPExplanationPanel from '../../components/SHAPExplanationPanel';
import RiskTimelineChart from '../../components/RiskTimelineChart';
import FeatureSnapshotPanel from '../../components/FeatureSnapshotPanel';
import AlertFeed from '../../components/AlertFeed';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import ErrorFallback from '../../components/ErrorFallback';
import { formatDistanceToNow } from 'date-fns';

export default function ProtocolDetail() {
  const router = useRouter();
  const { pool_id } = router.query;
  const [riskData, setRiskData] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [protocol, setProtocol] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPredicting, setIsPredicting] = useState(false);

  const API_URL = process.env.NEXT_PUBLIC_BACKEND_API || 'http://localhost:8001';

  const fetchData = async () => {
    if (!pool_id) return;

    try {
      setError(null);
      const [riskRes, historyRes, alertsRes, protocolsRes] = await Promise.all([
        axios.get(`${API_URL}/api/risk/latest/${encodeURIComponent(pool_id as string)}`).catch(() => null),
        axios.get(`${API_URL}/api/risk/history/${encodeURIComponent(pool_id as string)}?hours=48`).catch(() => ({ data: { records: [] } })),
        axios.get(`${API_URL}/api/risk/alerts?pool_id=${encodeURIComponent(pool_id as string)}`).catch(() => ({ data: { alerts: [] } })),
        axios.get(`${API_URL}/api/protocols`).catch(() => ({ data: [] })),
      ]);

      if (riskRes) setRiskData(riskRes.data);
      setHistory(historyRes?.data?.records || []);
      setAlerts(alertsRes?.data?.alerts || []);

      // Find protocol info
      const proto = protocolsRes?.data?.find((p: any) => p.pool_id === pool_id);
      setProtocol(proto);

      setLoading(false);
    } catch (err: any) {
      setError(err.message || 'Failed to load protocol data');
      setLoading(false);
    }
  };

  const handlePredict = async () => {
    if (!pool_id) return;
    setIsPredicting(true);
    try {
      await axios.post(`${API_URL}/api/risk/predict/${encodeURIComponent(pool_id as string)}`);
      await fetchData();
    } catch (err: any) {
      console.error('Prediction error:', err);
    } finally {
      setIsPredicting(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [pool_id]);

  if (!pool_id) return null;

  if (error && !riskData) {
    return (
      <div className="container mx-auto px-4 py-12">
        <Link href="/protocols" className="text-defi-primary hover:underline flex items-center gap-2 mb-6">
          <ArrowLeft className="w-4 h-4" />
          Back to Protocols
        </Link>
        <ErrorFallback error={error} onRetry={fetchData} />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Back link */}
      <Link href="/protocols" className="text-defi-primary hover:underline flex items-center gap-2 mb-6">
        <ArrowLeft className="w-4 h-4" />
        Back to Protocols
      </Link>

      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2" data-testid="pool-title">
            {pool_id}
          </h1>
          {protocol && (
            <div className="flex items-center gap-3">
              <span className="text-gray-400">{protocol.protocol}</span>
              <span className="px-2 py-0.5 text-xs rounded bg-dark-600 text-gray-400">
                {protocol.category}
              </span>
              {protocol.data_source === 'live' && (
                <span className="flex items-center gap-1 text-xs text-risk-low">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-risk-low opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-risk-low" />
                  </span>
                  Live Data
                </span>
              )}
            </div>
          )}
        </div>
        <div className="flex gap-3">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handlePredict}
            disabled={isPredicting}
            className="px-4 py-2 bg-defi-primary text-white rounded-lg flex items-center gap-2 disabled:opacity-50"
            data-testid="predict-button"
          >
            <RefreshCw className={`w-4 h-4 ${isPredicting ? 'animate-spin' : ''}`} />
            {isPredicting ? 'Predicting...' : 'Run Prediction'}
          </motion.button>
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <LoadingSkeleton type="gauge" />
            <LoadingSkeleton type="chart" />
          </div>
          <div className="space-y-6">
            <LoadingSkeleton type="card" />
            <LoadingSkeleton type="card" />
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Risk Score Card */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-card p-6"
            >
              <h2 className="text-xl font-semibold text-white mb-6">Current Risk Assessment</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
                {/* Gauge */}
                <div className="flex justify-center">
                  {riskData ? (
                    <RiskGaugeAnimated score={riskData.risk_score} size={280} />
                  ) : (
                    <div className="text-center py-12">
                      <p className="text-gray-400">No risk data available</p>
                      <button
                        onClick={handlePredict}
                        className="mt-4 px-4 py-2 bg-defi-primary text-white rounded-lg text-sm"
                      >
                        Generate Prediction
                      </button>
                    </div>
                  )}
                </div>

                {/* Info */}
                {riskData && (
                  <div className="space-y-4">
                    <div>
                      <div className="text-sm text-gray-500 mb-1">Risk Score</div>
                      <div className="text-5xl font-bold text-white" data-testid="risk-score">
                        {riskData.risk_score.toFixed(1)}
                        <span className="text-xl text-gray-500 font-normal">/100</span>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-3 bg-dark-800/50 rounded-lg">
                        <div className="text-xs text-gray-500 mb-1">Risk Level</div>
                        <div
                          className={`text-lg font-bold ${
                            riskData.risk_level === 'HIGH'
                              ? 'text-risk-high'
                              : riskData.risk_level === 'MEDIUM'
                              ? 'text-risk-medium'
                              : 'text-risk-low'
                          }`}
                        >
                          {riskData.risk_level}
                        </div>
                      </div>
                      {riskData.early_warning_score !== null && (
                        <div className="p-3 bg-dark-800/50 rounded-lg">
                          <div className="text-xs text-gray-500 mb-1">Early Warning</div>
                          <div className="text-lg font-bold text-defi-secondary">
                            {riskData.early_warning_score?.toFixed(1) || 'N/A'}
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="flex items-center gap-2 text-sm text-gray-400">
                      <Clock className="w-4 h-4" />
                      Updated {formatDistanceToNow(new Date(riskData.timestamp), { addSuffix: true })}
                    </div>

                    {riskData.model_version && (
                      <div className="text-xs text-gray-500">
                        Model: {riskData.model_version} • Horizon: {riskData.prediction_horizon || '1h'}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </motion.div>

            {/* Timeline Chart */}
            <RiskTimelineChart
              data={history.map((h) => ({
                timestamp: h.timestamp,
                risk_score: h.risk_score,
                risk_level: h.risk_level,
                has_alert: false,
              }))}
              loading={false}
            />
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* SHAP Explanation */}
            <SHAPExplanationPanel reasons={riskData?.top_reasons || []} />

            {/* Feature Snapshot */}
            {protocol && (
              <FeatureSnapshotPanel
                features={{
                  tvl: protocol.tvl,
                  volume_24h: protocol.volume_24h,
                }}
              />
            )}

            {/* Alerts for this pool */}
            {alerts.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass-card p-6"
              >
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-risk-high" />
                  Pool Alerts ({alerts.length})
                </h3>
                <AlertFeed alerts={alerts.slice(0, 3)} compact />
              </motion.div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
