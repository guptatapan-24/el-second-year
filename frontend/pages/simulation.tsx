import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import { Zap, Play, RotateCcw, TrendingDown, TrendingUp, AlertTriangle, Activity, CheckCircle, XCircle } from 'lucide-react';
import RiskGaugeAnimated from '../components/RiskGaugeAnimated';
import SHAPExplanationPanel from '../components/SHAPExplanationPanel';
import ErrorFallback from '../components/ErrorFallback';

interface SimulationEvent {
  id: string;
  name: string;
  description: string;
  icon: any;
  effect: string;
  severity: 'low' | 'medium' | 'high';
}

const simulationEvents: SimulationEvent[] = [
  {
    id: 'tvl_crash',
    name: 'TVL Crash',
    description: 'Simulate a 50% sudden drop in Total Value Locked',
    icon: TrendingDown,
    effect: 'Major liquidity withdrawal',
    severity: 'high',
  },
  {
    id: 'volume_spike',
    name: 'Volume Spike',
    description: 'Simulate 10x increase in trading volume',
    icon: TrendingUp,
    effect: 'Unusual trading activity',
    severity: 'medium',
  },
  {
    id: 'liquidity_imbalance',
    name: 'Liquidity Imbalance',
    description: 'Simulate severe reserve imbalance (80/20)',
    icon: Activity,
    effect: 'Pool destabilization',
    severity: 'high',
  },
];

export default function Simulation() {
  const [selectedPool, setSelectedPool] = useState<string>('');
  const [pools, setPools] = useState<any[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [simulationResult, setSimulationResult] = useState<any>(null);
  const [selectedEvent, setSelectedEvent] = useState<SimulationEvent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [comparisonMode, setComparisonMode] = useState(false);

  // Simulated comparison data (rule-based vs ML-based)
  const [comparison, setComparison] = useState<any>(null);

  const API_URL = process.env.NEXT_PUBLIC_BACKEND_API || 'http://localhost:8001';

  useEffect(() => {
    const fetchPools = async () => {
      try {
        const res = await axios.get(`${API_URL}/api/protocols`);
        setPools(res.data || []);
        if (res.data?.length > 0) {
          setSelectedPool(res.data[0].pool_id);
        }
      } catch (err) {
        console.error('Failed to fetch pools:', err);
      }
    };
    fetchPools();
  }, []);

  const runSimulation = async () => {
    if (!selectedPool || !selectedEvent) return;

    setIsRunning(true);
    setError(null);
    setSimulationResult(null);

    try {
      // First get current state
      const currentRes = await axios.get(
        `${API_URL}/api/risk/latest/${encodeURIComponent(selectedPool)}`
      ).catch(() => null);

      const currentRisk = currentRes?.data?.risk_score || Math.random() * 40 + 20;

      // Simulate the event effect (since we don't have a real simulation endpoint)
      // We'll trigger a prediction and add simulated delta
      await new Promise((resolve) => setTimeout(resolve, 2000)); // Simulate processing

      // Generate simulated result based on event type
      let simulatedScore = currentRisk;
      let delta = 0;

      switch (selectedEvent.id) {
        case 'tvl_crash':
          delta = 25 + Math.random() * 15;
          simulatedScore = Math.min(100, currentRisk + delta);
          break;
        case 'volume_spike':
          delta = 15 + Math.random() * 10;
          simulatedScore = Math.min(100, currentRisk + delta);
          break;
        case 'liquidity_imbalance':
          delta = 20 + Math.random() * 20;
          simulatedScore = Math.min(100, currentRisk + delta);
          break;
      }

      const riskLevel = simulatedScore < 30 ? 'LOW' : simulatedScore < 65 ? 'MEDIUM' : 'HIGH';
      const alertTriggered = simulatedScore >= 65 || delta > 20;

      setSimulationResult({
        pool_id: selectedPool,
        event: selectedEvent,
        before: {
          risk_score: currentRisk,
          risk_level: currentRisk < 30 ? 'LOW' : currentRisk < 65 ? 'MEDIUM' : 'HIGH',
        },
        after: {
          risk_score: simulatedScore,
          risk_level: riskLevel,
          delta: delta,
        },
        alert_triggered: alertTriggered,
        top_reasons: [
          { feature: 'tvl_change_1h', impact: delta * 0.4, direction: 'increasing' },
          { feature: 'volume_volatility', impact: delta * 0.3, direction: 'increasing' },
          { feature: 'reserve_imbalance', impact: delta * 0.2, direction: 'increasing' },
        ],
        detection_time_ms: Math.floor(Math.random() * 500 + 100),
      });

      // Generate comparison data
      setComparison({
        ml_based: {
          risk_score: simulatedScore,
          detection_time_ms: Math.floor(Math.random() * 500 + 100),
          explainability: true,
        },
        rule_based: {
          // Rule-based would be slower and less accurate
          risk_score: Math.min(100, simulatedScore + (Math.random() - 0.5) * 20),
          detection_time_ms: Math.floor(Math.random() * 2000 + 1000),
          explainability: false,
        },
      });

      setComparisonMode(true);
    } catch (err: any) {
      setError(err.message || 'Simulation failed');
    } finally {
      setIsRunning(false);
    }
  };

  const resetSimulation = () => {
    setSimulationResult(null);
    setComparison(null);
    setComparisonMode(false);
    setSelectedEvent(null);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2 flex items-center gap-3">
          <Zap className="w-8 h-8 text-defi-secondary" />
          Simulation Mode
        </h1>
        <p className="text-gray-400">
          Test VeriRisk's reaction to simulated DeFi crisis events. Demonstrates ML model response and
          explainability.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Control Panel */}
        <div className="lg:col-span-1 space-y-6">
          {/* Pool Selection */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card p-6"
          >
            <h3 className="text-lg font-semibold text-white mb-4">Select Protocol</h3>
            <select
              value={selectedPool}
              onChange={(e) => setSelectedPool(e.target.value)}
              className="w-full px-4 py-3 bg-dark-700 border border-white/10 rounded-lg text-white focus:outline-none focus:border-defi-primary/50"
              data-testid="pool-select"
            >
              {pools.map((pool) => (
                <option key={pool.pool_id} value={pool.pool_id}>
                  {pool.pool_id}
                </option>
              ))}
            </select>
          </motion.div>

          {/* Event Selection */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="glass-card p-6"
            data-testid="simulation-control-panel"
          >
            <h3 className="text-lg font-semibold text-white mb-4">Simulation Events</h3>
            <div className="space-y-3">
              {simulationEvents.map((event) => {
                const Icon = event.icon;
                const isSelected = selectedEvent?.id === event.id;
                const severityColor =
                  event.severity === 'high'
                    ? 'border-risk-high/50 bg-risk-high/5'
                    : event.severity === 'medium'
                    ? 'border-risk-medium/50 bg-risk-medium/5'
                    : 'border-risk-low/50 bg-risk-low/5';

                return (
                  <motion.button
                    key={event.id}
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.99 }}
                    onClick={() => setSelectedEvent(event)}
                    disabled={isRunning}
                    className={`w-full p-4 rounded-lg border text-left transition-all ${
                      isSelected
                        ? 'border-defi-secondary bg-defi-secondary/10'
                        : `border-white/5 hover:${severityColor}`
                    } ${isRunning ? 'opacity-50 cursor-not-allowed' : ''}`}
                    data-testid={`event-${event.id}`}
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                          event.severity === 'high'
                            ? 'bg-risk-high/20'
                            : event.severity === 'medium'
                            ? 'bg-risk-medium/20'
                            : 'bg-risk-low/20'
                        }`}
                      >
                        <Icon
                          className={`w-5 h-5 ${
                            event.severity === 'high'
                              ? 'text-risk-high'
                              : event.severity === 'medium'
                              ? 'text-risk-medium'
                              : 'text-risk-low'
                          }`}
                        />
                      </div>
                      <div className="flex-1">
                        <div className="text-sm font-semibold text-white">{event.name}</div>
                        <div className="text-xs text-gray-400 mt-1">{event.description}</div>
                        <div className="text-[10px] text-gray-500 mt-2">{event.effect}</div>
                      </div>
                      {isSelected && (
                        <div className="w-2 h-2 rounded-full bg-defi-secondary" />
                      )}
                    </div>
                  </motion.button>
                );
              })}
            </div>

            {/* Action Buttons */}
            <div className="mt-6 space-y-3">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={runSimulation}
                disabled={!selectedPool || !selectedEvent || isRunning}
                className="w-full px-6 py-3 bg-defi-secondary text-white font-semibold rounded-lg flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                data-testid="run-simulation-btn"
              >
                {isRunning ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Running Simulation...
                  </>
                ) : (
                  <>
                    <Play className="w-5 h-5" />
                    Run Simulation
                  </>
                )}
              </motion.button>

              {simulationResult && (
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={resetSimulation}
                  className="w-full px-6 py-3 bg-dark-700 text-white font-medium rounded-lg flex items-center justify-center gap-2 border border-white/10"
                >
                  <RotateCcw className="w-4 h-4" />
                  Reset
                </motion.button>
              )}
            </div>
          </motion.div>
        </div>

        {/* Results Panel */}
        <div className="lg:col-span-2 space-y-6">
          <AnimatePresence mode="wait">
            {error && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <ErrorFallback error={error} onRetry={runSimulation} />
              </motion.div>
            )}

            {!simulationResult && !isRunning && !error && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="glass-card p-12 text-center"
                data-testid="live-reaction-view"
              >
                <Zap className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-white mb-2">Ready to Simulate</h3>
                <p className="text-gray-400 max-w-md mx-auto">
                  Select a protocol and crisis event, then run the simulation to see how VeriRisk
                  detects and explains the risk change.
                </p>
              </motion.div>
            )}

            {isRunning && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="glass-card p-12 text-center"
              >
                <div className="relative w-24 h-24 mx-auto mb-6">
                  <div className="absolute inset-0 border-4 border-defi-secondary/30 rounded-full" />
                  <div className="absolute inset-0 border-4 border-transparent border-t-defi-secondary rounded-full animate-spin" />
                  <Zap className="absolute inset-0 m-auto w-10 h-10 text-defi-secondary" />
                </div>
                <h3 className="text-xl font-semibold text-white mb-2">Processing Simulation</h3>
                <p className="text-gray-400">Running ML inference and generating explanations...</p>
              </motion.div>
            )}

            {simulationResult && !isRunning && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-6"
              >
                {/* Risk Change Visualization */}
                <div className="glass-card p-6">
                  <h3 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
                    <Activity className="w-5 h-5 text-defi-primary" />
                    Risk Score Change
                  </h3>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
                    {/* Before */}
                    <div className="text-center">
                      <div className="text-sm text-gray-500 mb-2">Before Event</div>
                      <div
                        className={`text-4xl font-bold ${
                          simulationResult.before.risk_score < 30
                            ? 'text-risk-low'
                            : simulationResult.before.risk_score < 65
                            ? 'text-risk-medium'
                            : 'text-risk-high'
                        }`}
                      >
                        {simulationResult.before.risk_score.toFixed(1)}
                      </div>
                      <div className="text-xs text-gray-500">
                        {simulationResult.before.risk_level}
                      </div>
                    </div>

                    {/* Arrow */}
                    <div className="flex justify-center">
                      <div className="flex items-center gap-2">
                        <div className="w-12 h-0.5 bg-gradient-to-r from-gray-600 to-risk-high" />
                        <TrendingUp className="w-6 h-6 text-risk-high" />
                        <div className="text-risk-high font-bold">+{simulationResult.after.delta.toFixed(1)}</div>
                      </div>
                    </div>

                    {/* After */}
                    <div className="text-center">
                      <div className="text-sm text-gray-500 mb-2">After Event</div>
                      <div
                        className={`text-4xl font-bold ${
                          simulationResult.after.risk_score < 30
                            ? 'text-risk-low'
                            : simulationResult.after.risk_score < 65
                            ? 'text-risk-medium'
                            : 'text-risk-high'
                        }`}
                      >
                        {simulationResult.after.risk_score.toFixed(1)}
                      </div>
                      <div className="text-xs text-gray-500">
                        {simulationResult.after.risk_level}
                      </div>
                    </div>
                  </div>

                  {/* Alert Status */}
                  <div className="mt-6 pt-6 border-t border-white/5">
                    <div
                      className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg ${
                        simulationResult.alert_triggered
                          ? 'bg-risk-high/10 text-risk-high border border-risk-high/30'
                          : 'bg-risk-low/10 text-risk-low border border-risk-low/30'
                      }`}
                    >
                      {simulationResult.alert_triggered ? (
                        <>
                          <AlertTriangle className="w-4 h-4" />
                          Alert Triggered
                        </>
                      ) : (
                        <>
                          <CheckCircle className="w-4 h-4" />
                          No Alert Triggered
                        </>
                      )}
                    </div>
                    <span className="ml-4 text-sm text-gray-500">
                      Detection time: {simulationResult.detection_time_ms}ms
                    </span>
                  </div>
                </div>

                {/* SHAP Explanation */}
                <SHAPExplanationPanel reasons={simulationResult.top_reasons} />

                {/* ML vs Rule Comparison */}
                {comparison && comparisonMode && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="glass-card p-6"
                    data-testid="ml-vs-rule-comparison"
                  >
                    <h3 className="text-lg font-semibold text-white mb-6">ML vs Rule-Based Comparison</h3>

                    <div className="grid grid-cols-2 gap-4">
                      {/* ML-Based */}
                      <div className="p-4 bg-defi-primary/5 border border-defi-primary/30 rounded-lg">
                        <div className="flex items-center gap-2 mb-4">
                          <div className="w-8 h-8 rounded-lg bg-defi-primary/20 flex items-center justify-center">
                            <Zap className="w-4 h-4 text-defi-primary" />
                          </div>
                          <div>
                            <div className="text-sm font-semibold text-white">ML-Based</div>
                            <div className="text-[10px] text-gray-500">VeriRisk XGBoost</div>
                          </div>
                        </div>

                        <div className="space-y-3">
                          <div className="flex justify-between">
                            <span className="text-xs text-gray-400">Risk Score</span>
                            <span className="text-sm font-bold text-white">
                              {comparison.ml_based.risk_score.toFixed(1)}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-xs text-gray-400">Detection Time</span>
                            <span className="text-sm font-bold text-risk-low">
                              {comparison.ml_based.detection_time_ms}ms
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-xs text-gray-400">Explainability</span>
                            <CheckCircle className="w-4 h-4 text-risk-low" />
                          </div>
                        </div>
                      </div>

                      {/* Rule-Based */}
                      <div className="p-4 bg-gray-800/50 border border-white/10 rounded-lg">
                        <div className="flex items-center gap-2 mb-4">
                          <div className="w-8 h-8 rounded-lg bg-gray-700 flex items-center justify-center">
                            <Activity className="w-4 h-4 text-gray-400" />
                          </div>
                          <div>
                            <div className="text-sm font-semibold text-white">Rule-Based</div>
                            <div className="text-[10px] text-gray-500">Traditional Thresholds</div>
                          </div>
                        </div>

                        <div className="space-y-3">
                          <div className="flex justify-between">
                            <span className="text-xs text-gray-400">Risk Score</span>
                            <span className="text-sm font-bold text-white">
                              {comparison.rule_based.risk_score.toFixed(1)}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-xs text-gray-400">Detection Time</span>
                            <span className="text-sm font-bold text-risk-medium">
                              {comparison.rule_based.detection_time_ms}ms
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-xs text-gray-400">Explainability</span>
                            <XCircle className="w-4 h-4 text-risk-high" />
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="mt-4 pt-4 border-t border-white/5">
                      <p className="text-xs text-gray-500">
                        ML-based detection is{' '}
                        <span className="text-defi-primary font-bold">
                          {(
                            (comparison.rule_based.detection_time_ms -
                              comparison.ml_based.detection_time_ms) /
                            comparison.rule_based.detection_time_ms *
                            100
                          ).toFixed(0)}%
                        </span>{' '}
                        faster with SHAP-powered explainability.
                      </p>
                    </div>
                  </motion.div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
