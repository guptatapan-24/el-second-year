import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import axios from 'axios';
import { RefreshCw, Download, TrendingUp, TrendingDown, Database, Brain, Loader2 } from 'lucide-react';
import ProtocolRiskCard from '../../components/ProtocolRiskCard';
import RiskFilter from '../../components/RiskFilter';
import GlobalStats from '../../components/GlobalStats';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import ErrorFallback from '../../components/ErrorFallback';

interface Protocol {
  pool_id: string;
  protocol: string;
  category: string;
  tvl: number;
  volume_24h: number;
  last_update: string;
  data_source?: string;
}

interface RiskData {
  pool_id: string;
  latest_risk_score: number;
  latest_risk_level: string;
  active_alerts: number;
}

interface DataStatus {
  total_snapshots: number;
  pool_count: number;
  hours_of_history: number;
  model_trained: boolean;
  data_ready: boolean;
  init_status: {
    running: boolean;
    phase: string;
    progress: number;
    error: string | null;
    completed: boolean;
  };
}

export default function Protocols() {
  const [protocols, setProtocols] = useState<Protocol[]>([]);
  const [risks, setRisks] = useState<Map<string, RiskData>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isFetching, setIsFetching] = useState(false);
  const [isInitializing, setIsInitializing] = useState(false);
  const [dataStatus, setDataStatus] = useState<DataStatus | null>(null);

  // Filter states
  const [selectedRiskLevel, setSelectedRiskLevel] = useState('All');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [selectedProtocol, setSelectedProtocol] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');

  const API_URL = process.env.NEXT_PUBLIC_BACKEND_API || 'http://localhost:8001';

  const fetchData = async () => {
    try {
      setError(null);
      const [protocolsRes, summaryRes, statusRes] = await Promise.all([
        axios.get(`${API_URL}/api/protocols`),
        axios.get(`${API_URL}/api/risk/summary`),
        axios.get(`${API_URL}/api/protocols/status`),
      ]);

      setProtocols(protocolsRes.data);
      setDataStatus(statusRes.data);

      // Create risk map from summary
      const riskMap = new Map<string, RiskData>();
      summaryRes.data.pools?.forEach((pool: RiskData) => {
        riskMap.set(pool.pool_id, pool);
      });
      setRisks(riskMap);
      
      // Check if initialization is running
      if (statusRes.data.init_status?.running) {
        setIsInitializing(true);
      } else {
        setIsInitializing(false);
      }
      
      setLoading(false);
    } catch (err: any) {
      setError(err.message || 'Failed to load protocols');
      setLoading(false);
    }
  };

  const handleInitialize = async () => {
    setIsInitializing(true);
    try {
      await axios.post(`${API_URL}/api/protocols/initialize?days=30`);
      // Start polling for status
      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await axios.get(`${API_URL}/api/protocols/status`);
          setDataStatus(statusRes.data);
          
          if (!statusRes.data.init_status?.running) {
            clearInterval(pollInterval);
            setIsInitializing(false);
            await fetchData();
          }
        } catch (e) {
          console.error('Poll error:', e);
        }
      }, 2000);
    } catch (err: any) {
      console.error('Initialize error:', err);
      setIsInitializing(false);
    }
  };

  const handleFetchProtocols = async () => {
    setIsFetching(true);
    try {
      await axios.post(`${API_URL}/api/protocols/fetch`);
      // Also trigger predictions
      await axios.post(`${API_URL}/api/risk/predict-all`);
      await fetchData();
    } catch (err: any) {
      console.error('Error fetching protocols:', err);
    } finally {
      setIsFetching(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  // Filter and sort protocols
  const filteredProtocols = useMemo(() => {
    return protocols
      .filter((p) => {
        // Risk level filter
        if (selectedRiskLevel !== 'All') {
          const risk = risks.get(p.pool_id);
          if (!risk || risk.latest_risk_level !== selectedRiskLevel) return false;
        }
        // Category filter
        if (selectedCategory !== 'All' && p.category !== selectedCategory) return false;
        // Protocol filter
        if (selectedProtocol !== 'All' && p.protocol !== selectedProtocol) return false;
        // Search filter
        if (searchQuery) {
          const query = searchQuery.toLowerCase();
          return (
            p.pool_id.toLowerCase().includes(query) ||
            p.protocol.toLowerCase().includes(query)
          );
        }
        return true;
      })
      .sort((a, b) => {
        // Sort by risk score (highest first)
        const riskA = risks.get(a.pool_id)?.latest_risk_score ?? 0;
        const riskB = risks.get(b.pool_id)?.latest_risk_score ?? 0;
        return riskB - riskA;
      });
  }, [protocols, risks, selectedRiskLevel, selectedCategory, selectedProtocol, searchQuery]);

  // Calculate stats
  const stats = useMemo(() => {
    const totalTVL = filteredProtocols.reduce((sum, p) => sum + p.tvl, 0);
    const avgRisk =
      filteredProtocols.length > 0
        ? filteredProtocols.reduce(
            (sum, p) => sum + (risks.get(p.pool_id)?.latest_risk_score || 0),
            0
          ) / filteredProtocols.length
        : 0;
    const highRiskCount = filteredProtocols.filter(
      (p) => risks.get(p.pool_id)?.latest_risk_level === 'HIGH'
    ).length;
    const alertsCount = filteredProtocols.reduce(
      (sum, p) => sum + (risks.get(p.pool_id)?.active_alerts || 0),
      0
    );

    return { totalTVL, avgRisk, highRiskCount, alertsCount };
  }, [filteredProtocols, risks]);

  // Get unique protocols for filter
  const uniqueProtocols = useMemo(() => {
    const set = new Set(protocols.map((p) => p.protocol));
    return ['All', ...Array.from(set)];
  }, [protocols]);

  if (error) {
    return (
      <div className="container mx-auto px-4 py-12">
        <ErrorFallback error={error} onRetry={fetchData} />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Protocol Dashboard</h1>
          <p className="text-gray-400">
            ML-driven risk monitoring across {protocols.length} DeFi protocols
          </p>
        </div>
        <div className="flex gap-3">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={fetchData}
            className="px-4 py-2 bg-dark-700 text-white rounded-lg flex items-center gap-2 border border-white/10 hover:border-defi-primary/50 transition-colors"
            data-testid="refresh-button"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </motion.button>
          
          {/* Initialize button - shown when no data */}
          {(!dataStatus?.data_ready || !dataStatus?.model_trained) && !isInitializing && (
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleInitialize}
              className="px-4 py-2 bg-defi-secondary text-white rounded-lg flex items-center gap-2"
              data-testid="initialize-button"
            >
              <Database className="w-4 h-4" />
              Initialize System
            </motion.button>
          )}
          
          {/* Initializing indicator */}
          {isInitializing && (
            <div className="px-4 py-2 bg-dark-700 text-defi-primary rounded-lg flex items-center gap-2 border border-defi-primary/30">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm">
                {dataStatus?.init_status?.phase || 'Initializing...'}
                {dataStatus?.init_status?.progress ? ` (${dataStatus.init_status.progress}%)` : ''}
              </span>
            </div>
          )}
          
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleFetchProtocols}
            disabled={isFetching || isInitializing}
            className="px-4 py-2 bg-defi-primary text-white rounded-lg flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="fetch-protocols-button"
          >
            <Download className={`w-4 h-4 ${isFetching ? 'animate-bounce' : ''}`} />
            {isFetching ? 'Fetching...' : 'Fetch & Predict'}
          </motion.button>
        </div>
      </div>

      {/* Stats */}
      <div className="mb-8">
        <GlobalStats
          totalProtocols={filteredProtocols.length}
          highRiskCount={stats.highRiskCount}
          alertsToday={stats.alertsCount}
          totalTVL={stats.totalTVL}
          avgRisk={stats.avgRisk}
          loading={loading}
        />
      </div>

      {/* Filters */}
      <RiskFilter
        selectedRiskLevel={selectedRiskLevel}
        onRiskLevelChange={setSelectedRiskLevel}
        selectedCategory={selectedCategory}
        onCategoryChange={setSelectedCategory}
        selectedProtocol={selectedProtocol}
        onProtocolChange={setSelectedProtocol}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        protocols={uniqueProtocols}
      />

      {/* Protocol Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <LoadingSkeleton type="card" count={6} />
        </div>
      ) : filteredProtocols.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-16 glass-card"
        >
          {!dataStatus?.data_ready || !dataStatus?.model_trained ? (
            <>
              <Database className="w-16 h-16 text-defi-primary mx-auto mb-4" />
              <p className="text-xl text-white mb-2">System Not Initialized</p>
              <p className="text-gray-400 mb-6">
                Initialize VeriRisk with real DeFi protocol data from DeFiLlama
              </p>
              {isInitializing ? (
                <div className="inline-flex items-center gap-2 px-6 py-3 bg-dark-700 text-defi-primary rounded-lg">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>{dataStatus?.init_status?.phase || 'Initializing...'}</span>
                  {dataStatus?.init_status?.progress && (
                    <span className="text-sm">({dataStatus.init_status.progress}%)</span>
                  )}
                </div>
              ) : (
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleInitialize}
                  className="px-6 py-3 bg-gradient-to-r from-defi-primary to-defi-secondary text-white rounded-lg flex items-center gap-2 mx-auto"
                  data-testid="init-system-button"
                >
                  <Database className="w-5 h-5" />
                  Initialize with Real Data
                </motion.button>
              )}
              <p className="text-xs text-gray-500 mt-4">
                This will fetch 30 days of historical data and train the ML model
              </p>
            </>
          ) : (
            <>
              <p className="text-xl text-gray-400 mb-4">No protocols match your filters</p>
              <p className="text-gray-500 mb-6">Try adjusting filters or fetch new protocol data</p>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleFetchProtocols}
                disabled={isFetching}
                className="px-6 py-3 bg-defi-primary text-white rounded-lg"
              >
                {isFetching ? 'Fetching...' : 'Fetch Protocol Data'}
              </motion.button>
            </>
          )}
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredProtocols.map((protocol, idx) => {
            const risk = risks.get(protocol.pool_id);
            return (
              <ProtocolRiskCard
                key={protocol.pool_id}
                pool_id={protocol.pool_id}
                protocol={protocol.protocol}
                category={protocol.category}
                tvl={protocol.tvl}
                volume_24h={protocol.volume_24h}
                risk_score={risk?.latest_risk_score}
                risk_level={risk?.latest_risk_level}
                trend={risk && risk.latest_risk_score > 50 ? 'up' : risk && risk.latest_risk_score < 30 ? 'down' : 'stable'}
                last_update={protocol.last_update}
                data_source={protocol.data_source}
                index={idx}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
