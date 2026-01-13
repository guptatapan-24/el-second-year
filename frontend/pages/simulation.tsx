import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import { 
  Zap, Play, RotateCcw, TrendingDown, TrendingUp, AlertTriangle, 
  Activity, CheckCircle, XCircle, RefreshCw, Sliders, Sparkles,
  ArrowRight, Info
} from 'lucide-react';
import RiskGaugeAnimated from '../components/RiskGaugeAnimated';
import SHAPExplanationPanel from '../components/SHAPExplanationPanel';
import ErrorFallback from '../components/ErrorFallback';

interface SimulationParams {
  tvl_change_pct: number;
  volume_change_pct: number;
  volatility_override: number | null;
  reserve_imbalance_override: number | null;
}

interface SimulationResult {
  pool_id: string;
  timestamp: string;
  simulation_params: SimulationParams;
  actual_risk: {
    score: number;
    level: string;
    early_warning_score?: number;
  };
  simulated_risk: {
    score: number;
    level: string;
    early_warning_score?: number;
  };
  delta: number;
  risk_increased: boolean;
  alert_would_trigger: boolean;
  top_risk_factors: Array<{
    feature: string;
    impact: number;
    direction: string;
    explanation?: string;
  }>;
  feature_changes: Record<string, { before: number; after: number }>;
}

interface Preset {
  id: string;
  name: string;
  description: string;
  params: {
    tvl_change_pct?: number;
    volume_change_pct?: number;
    volatility_override?: number;
    reserve_imbalance_override?: number;
  };
  severity: string;
  real_world_example: string;
}

const severityColors: Record<string, string> = {
  LOW: 'border-risk-low/50 bg-risk-low/5 text-risk-low',
  MEDIUM: 'border-risk-medium/50 bg-risk-medium/5 text-risk-medium',
  HIGH: 'border-risk-high/50 bg-risk-high/5 text-risk-high',
  CRITICAL: 'border-red-600/50 bg-red-600/5 text-red-500',
};

export default function Simulation() {
  const [selectedPool, setSelectedPool] = useState<string>('');
  const [pools, setPools] = useState<any[]>([]);
  const [presets, setPresets] = useState<Preset[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [simulationResult, setSimulationResult] = useState<SimulationResult | null>(null);
  const [selectedPreset, setSelectedPreset] = useState<Preset | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Simulation parameters with sliders
  const [tvlChange, setTvlChange] = useState(0);
  const [volumeChange, setVolumeChange] = useState(0);
  const [volatilityOverride, setVolatilityOverride] = useState<number | null>(null);
  const [reserveImbalanceOverride, setReserveImbalanceOverride] = useState<number | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_BACKEND_API || 'http://localhost:8001';

  // Fetch pools
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
  }, [API_URL]);

  // Fetch presets
  useEffect(() => {
    const fetchPresets = async () => {
      try {
        const res = await axios.get(`${API_URL}/api/risk/simulate/presets`);
        setPresets(res.data.presets || []);
      } catch (err) {
        console.error('Failed to fetch presets:', err);
      }
    };
    fetchPresets();
  }, [API_URL]);

  // Apply preset values
  const applyPreset = useCallback((preset: Preset) => {
    setSelectedPreset(preset);
    setTvlChange(preset.params.tvl_change_pct || 0);
    setVolumeChange(preset.params.volume_change_pct || 0);
    setVolatilityOverride(preset.params.volatility_override || null);
    setReserveImbalanceOverride(preset.params.reserve_imbalance_override || null);
  }, []);

  // Run simulation against real API
  const runSimulation = async () => {
    if (!selectedPool) return;

    setIsRunning(true);
    setError(null);
    setSimulationResult(null);

    try {
      const payload: any = {
        pool_id: selectedPool,
        tvl_change_pct: tvlChange,
        volume_change_pct: volumeChange,
      };

      if (volatilityOverride !== null) {
        payload.volatility_override = volatilityOverride;
      }
      if (reserveImbalanceOverride !== null) {
        payload.reserve_imbalance_override = reserveImbalanceOverride;
      }

      const res = await axios.post(`${API_URL}/api/risk/simulate`, payload);
      setSimulationResult(res.data);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Simulation failed';
      setError(errorMessage);
    } finally {
      setIsRunning(false);
    }
  };

  const resetSimulation = () => {
    setSimulationResult(null);
    setSelectedPreset(null);
    setTvlChange(0);
    setVolumeChange(0);
    setVolatilityOverride(null);
    setReserveImbalanceOverride(null);
    setError(null);
  };

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'LOW': return 'text-risk-low';
      case 'MEDIUM': return 'text-risk-medium';
      case 'HIGH': return 'text-risk-high';
      default: return 'text-gray-400';
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2 flex items-center gap-3">
          <div className="relative">
            <Zap className="w-8 h-8 text-defi-secondary" />
            <div className="absolute inset-0 animate-ping opacity-30">
              <Zap className="w-8 h-8 text-defi-secondary" />
            </div>
          </div>
          Risk Simulation Engine
        </h1>
        <p className="text-gray-400">
          Test VeriRisk's ML-powered risk detection with what-if scenarios. 
          Simulate market shocks and see predicted impact in real-time.
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
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Activity className="w-5 h-5 text-defi-primary" />
              Select Protocol
            </h3>
            <select
              value={selectedPool}
              onChange={(e) => setSelectedPool(e.target.value)}
              className="w-full px-4 py-3 bg-dark-700 border border-white/10 rounded-lg text-white focus:outline-none focus:border-defi-primary/50 transition-colors"
              data-testid="pool-select"
            >
              {pools.map((pool) => (
                <option key={pool.pool_id} value={pool.pool_id}>
                  {pool.pool_id}
                </option>
              ))}
            </select>
          </motion.div>

          {/* Simulation Presets */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="glass-card p-6"
          >
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-defi-secondary" />
              Crisis Scenarios
            </h3>
            <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2">
              {presets.map((preset) => {
                const isSelected = selectedPreset?.id === preset.id;
                const colorClass = severityColors[preset.severity] || severityColors.MEDIUM;

                return (
                  <motion.button
                    key={preset.id}
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.99 }}
                    onClick={() => applyPreset(preset)}
                    disabled={isRunning}
                    className={`w-full p-4 rounded-lg border text-left transition-all ${
                      isSelected
                        ? 'border-defi-secondary bg-defi-secondary/10 ring-1 ring-defi-secondary/50'
                        : `border-white/5 hover:border-white/20 ${colorClass.split(' ')[0]} hover:bg-dark-700`
                    } ${isRunning ? 'opacity-50 cursor-not-allowed' : ''}`}
                    data-testid={`preset-${preset.id}`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-white">{preset.name}</span>
                          <span className={`px-1.5 py-0.5 text-[10px] font-bold rounded ${colorClass}`}>
                            {preset.severity}
                          </span>
                        </div>
                        <p className="text-xs text-gray-400 mt-1">{preset.description}</p>
                        <p className="text-[10px] text-gray-500 mt-2 italic">
                          Example: {preset.real_world_example}
                        </p>
                      </div>
                      {isSelected && (
                        <div className="w-2 h-2 rounded-full bg-defi-secondary animate-pulse" />
                      )}
                    </div>
                  </motion.button>
                );
              })}
            </div>
          </motion.div>

          {/* Parameter Sliders */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="glass-card p-6"
            data-testid="simulation-control-panel"
          >
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Sliders className="w-5 h-5 text-defi-primary" />
              Simulation Parameters
            </h3>

            {/* TVL Change Slider */}
            <div className="mb-6">
              <div className="flex justify-between mb-2">
                <label className="text-sm text-gray-400">TVL Change</label>
                <span className={`text-sm font-mono font-bold ${tvlChange < 0 ? 'text-risk-high' : tvlChange > 0 ? 'text-risk-low' : 'text-white'}`}>
                  {tvlChange > 0 ? '+' : ''}{tvlChange}%
                </span>
              </div>
              <input
                type="range"
                min="-80"
                max="80"
                step="1"
                value={tvlChange}
                onChange={(e) => setTvlChange(Number(e.target.value))}
                className="w-full h-2 bg-dark-700 rounded-lg appearance-none cursor-pointer slider-thumb"
                data-testid="tvl-slider"
              />
              <div className="flex justify-between text-[10px] text-gray-600 mt-1">
                <span>-80%</span>
                <span>0%</span>
                <span>+80%</span>
              </div>
            </div>

            {/* Volume Change Slider */}
            <div className="mb-6">
              <div className="flex justify-between mb-2">
                <label className="text-sm text-gray-400">Volume Change</label>
                <span className={`text-sm font-mono font-bold ${volumeChange > 100 ? 'text-risk-medium' : 'text-white'}`}>
                  {volumeChange > 0 ? '+' : ''}{volumeChange}%
                </span>
              </div>
              <input
                type="range"
                min="-100"
                max="200"
                step="5"
                value={volumeChange}
                onChange={(e) => setVolumeChange(Number(e.target.value))}
                className="w-full h-2 bg-dark-700 rounded-lg appearance-none cursor-pointer slider-thumb"
                data-testid="volume-slider"
              />
              <div className="flex justify-between text-[10px] text-gray-600 mt-1">
                <span>-100%</span>
                <span>0%</span>
                <span>+200%</span>
              </div>
            </div>

            {/* Advanced Options Toggle */}
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-xs text-defi-primary hover:text-defi-primary/80 flex items-center gap-1 mb-4"
            >
              <Info className="w-3 h-3" />
              {showAdvanced ? 'Hide' : 'Show'} Advanced Options
            </button>

            {/* Advanced Options */}
            <AnimatePresence>
              {showAdvanced && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="space-y-4 border-t border-white/10 pt-4"
                >
                  {/* Volatility Override */}
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <label className="text-sm text-gray-400">Volatility Override</label>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-mono font-bold text-white">
                          {volatilityOverride !== null ? volatilityOverride.toFixed(2) : 'Auto'}
                        </span>
                        {volatilityOverride !== null && (
                          <button
                            onClick={() => setVolatilityOverride(null)}
                            className="text-[10px] text-gray-500 hover:text-white"
                          >
                            Reset
                          </button>
                        )}
                      </div>
                    </div>
                    <input
                      type="range"
                      min="0.01"
                      max="0.5"
                      step="0.01"
                      value={volatilityOverride || 0.02}
                      onChange={(e) => setVolatilityOverride(Number(e.target.value))}
                      className="w-full h-2 bg-dark-700 rounded-lg appearance-none cursor-pointer slider-thumb"
                      data-testid="volatility-slider"
                    />
                    <div className="flex justify-between text-[10px] text-gray-600 mt-1">
                      <span>Low (0.01)</span>
                      <span>High (0.5)</span>
                    </div>
                  </div>

                  {/* Reserve Imbalance Override */}
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <label className="text-sm text-gray-400">Reserve Imbalance</label>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-mono font-bold text-white">
                          {reserveImbalanceOverride !== null ? (reserveImbalanceOverride * 100).toFixed(0) + '%' : 'Auto'}
                        </span>
                        {reserveImbalanceOverride !== null && (
                          <button
                            onClick={() => setReserveImbalanceOverride(null)}
                            className="text-[10px] text-gray-500 hover:text-white"
                          >
                            Reset
                          </button>
                        )}
                      </div>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.05"
                      value={reserveImbalanceOverride || 0}
                      onChange={(e) => setReserveImbalanceOverride(Number(e.target.value))}
                      className="w-full h-2 bg-dark-700 rounded-lg appearance-none cursor-pointer slider-thumb"
                      data-testid="imbalance-slider"
                    />
                    <div className="flex justify-between text-[10px] text-gray-600 mt-1">
                      <span>Balanced</span>
                      <span>Severe</span>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Action Buttons */}
            <div className="mt-6 space-y-3">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={runSimulation}
                disabled={!selectedPool || isRunning}
                className="w-full px-6 py-3 bg-gradient-to-r from-defi-secondary to-defi-primary text-white font-semibold rounded-lg flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-glow-purple hover:shadow-glow-cyan transition-shadow"
                data-testid="run-simulation-btn"
              >
                {isRunning ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Running ML Inference...
                  </>
                ) : (
                  <>
                    <Play className="w-5 h-5" />
                    Run Simulation
                  </>
                )}
              </motion.button>

              {(simulationResult || error) && (
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={resetSimulation}
                  className="w-full px-6 py-3 bg-dark-700 text-white font-medium rounded-lg flex items-center justify-center gap-2 border border-white/10 hover:border-white/30 transition-colors"
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
                <div className="relative w-20 h-20 mx-auto mb-6">
                  <div className="absolute inset-0 bg-defi-secondary/10 rounded-2xl animate-pulse" />
                  <Zap className="absolute inset-0 m-auto w-10 h-10 text-defi-secondary" />
                </div>
                <h3 className="text-xl font-semibold text-white mb-2">Ready to Simulate</h3>
                <p className="text-gray-400 max-w-md mx-auto mb-6">
                  Select a protocol and adjust parameters or choose a crisis scenario, 
                  then run the simulation to see ML-powered risk predictions.
                </p>
                <div className="flex flex-wrap justify-center gap-3 text-xs text-gray-500">
                  <span className="flex items-center gap-1">
                    <CheckCircle className="w-3 h-3 text-risk-low" />
                    Real ML Inference
                  </span>
                  <span className="flex items-center gap-1">
                    <CheckCircle className="w-3 h-3 text-risk-low" />
                    SHAP Explanations
                  </span>
                  <span className="flex items-center gap-1">
                    <CheckCircle className="w-3 h-3 text-risk-low" />
                    Feature Analysis
                  </span>
                </div>
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
                  <div className="absolute inset-2 border-4 border-transparent border-t-defi-primary rounded-full animate-spin" style={{ animationDirection: 'reverse', animationDuration: '0.8s' }} />
                  <Zap className="absolute inset-0 m-auto w-10 h-10 text-defi-secondary animate-pulse" />
                </div>
                <h3 className="text-xl font-semibold text-white mb-2">Processing Simulation</h3>
                <p className="text-gray-400">Running XGBoost inference and generating SHAP explanations...</p>
              </motion.div>
            )}

            {simulationResult && !isRunning && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-6"
              >
                {/* Risk Change Visualization */}
                <div className="glass-card p-6 overflow-hidden relative">
                  {/* Background glow effect */}
                  <div className={`absolute inset-0 opacity-20 blur-3xl ${
                    simulationResult.risk_increased ? 'bg-risk-high' : 'bg-risk-low'
                  }`} />
                  
                  <h3 className="text-lg font-semibold text-white mb-6 flex items-center gap-2 relative z-10">
                    <Activity className="w-5 h-5 text-defi-primary" />
                    Risk Score Comparison
                  </h3>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-center relative z-10">
                    {/* Before (Actual) */}
                    <div className="text-center p-4 rounded-xl bg-dark-800/50 border border-white/5">
                      <div className="text-sm text-gray-500 mb-3 flex items-center justify-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-gray-500" />
                        Current State
                      </div>
                      <div
                        className={`text-5xl font-bold ${getRiskColor(simulationResult.actual_risk.level)}`}
                      >
                        {simulationResult.actual_risk.score.toFixed(1)}
                      </div>
                      <div className={`text-xs mt-2 px-2 py-1 rounded inline-block ${
                        simulationResult.actual_risk.level === 'LOW' ? 'bg-risk-low/20 text-risk-low' :
                        simulationResult.actual_risk.level === 'MEDIUM' ? 'bg-risk-medium/20 text-risk-medium' :
                        'bg-risk-high/20 text-risk-high'
                      }`}>
                        {simulationResult.actual_risk.level}
                      </div>
                    </div>

                    {/* Arrow with Delta */}
                    <div className="flex flex-col items-center justify-center">
                      <div className="flex items-center gap-2 mb-2">
                        <div className="w-8 h-0.5 bg-gradient-to-r from-gray-600 to-defi-secondary" />
                        <motion.div
                          animate={{ x: [0, 5, 0] }}
                          transition={{ repeat: Infinity, duration: 1.5 }}
                        >
                          <ArrowRight className={`w-6 h-6 ${
                            simulationResult.risk_increased ? 'text-risk-high' : 'text-risk-low'
                          }`} />
                        </motion.div>
                        <div className="w-8 h-0.5 bg-gradient-to-r from-defi-secondary to-gray-600" />
                      </div>
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        className={`text-2xl font-bold px-4 py-2 rounded-lg ${
                          simulationResult.delta >= 0 
                            ? 'bg-risk-high/10 text-risk-high border border-risk-high/30' 
                            : 'bg-risk-low/10 text-risk-low border border-risk-low/30'
                        }`}
                      >
                        {simulationResult.delta >= 0 ? '+' : ''}{simulationResult.delta.toFixed(1)}
                      </motion.div>
                      <span className="text-[10px] text-gray-500 mt-1">Delta</span>
                    </div>

                    {/* After (Simulated) */}
                    <div className="text-center p-4 rounded-xl bg-dark-800/50 border border-white/5">
                      <div className="text-sm text-gray-500 mb-3 flex items-center justify-center gap-1">
                        <span className={`w-2 h-2 rounded-full ${
                          simulationResult.risk_increased ? 'bg-risk-high animate-pulse' : 'bg-risk-low'
                        }`} />
                        Simulated State
                      </div>
                      <div
                        className={`text-5xl font-bold ${getRiskColor(simulationResult.simulated_risk.level)}`}
                      >
                        {simulationResult.simulated_risk.score.toFixed(1)}
                      </div>
                      <div className={`text-xs mt-2 px-2 py-1 rounded inline-block ${
                        simulationResult.simulated_risk.level === 'LOW' ? 'bg-risk-low/20 text-risk-low' :
                        simulationResult.simulated_risk.level === 'MEDIUM' ? 'bg-risk-medium/20 text-risk-medium' :
                        'bg-risk-high/20 text-risk-high'
                      }`}>
                        {simulationResult.simulated_risk.level}
                      </div>
                    </div>
                  </div>

                  {/* Alert Status */}
                  <div className="mt-6 pt-6 border-t border-white/5 relative z-10">
                    <div className="flex flex-wrap items-center gap-4">
                      <motion.div
                        initial={{ x: -20, opacity: 0 }}
                        animate={{ x: 0, opacity: 1 }}
                        className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg ${
                          simulationResult.alert_would_trigger
                            ? 'bg-risk-high/10 text-risk-high border border-risk-high/30 shadow-glow-red'
                            : 'bg-risk-low/10 text-risk-low border border-risk-low/30'
                        }`}
                      >
                        {simulationResult.alert_would_trigger ? (
                          <>
                            <AlertTriangle className="w-4 h-4 animate-pulse" />
                            <span className="font-medium">Alert Would Trigger</span>
                          </>
                        ) : (
                          <>
                            <CheckCircle className="w-4 h-4" />
                            <span className="font-medium">No Alert Triggered</span>
                          </>
                        )}
                      </motion.div>

                      {simulationResult.delta >= 30 && (
                        <motion.div
                          initial={{ x: -20, opacity: 0 }}
                          animate={{ x: 0, opacity: 1 }}
                          transition={{ delay: 0.2 }}
                          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-defi-secondary/10 text-defi-secondary border border-defi-secondary/30"
                        >
                          <Zap className="w-4 h-4" />
                          <span className="font-medium">RISK_SPIKE Detected</span>
                        </motion.div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Feature Changes */}
                <div className="glass-card p-6">
                  <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <RefreshCw className="w-5 h-5 text-defi-primary" />
                    Feature Changes Applied
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {Object.entries(simulationResult.feature_changes).map(([key, value]) => (
                      <div key={key} className="p-3 bg-dark-700/50 rounded-lg border border-white/5">
                        <div className="text-[10px] text-gray-500 mb-1">{key.replace(/_/g, ' ')}</div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-gray-400">{value.before.toFixed(2)}</span>
                          <ArrowRight className="w-3 h-3 text-gray-500" />
                          <span className={`text-xs font-medium ${
                            value.after > value.before ? 'text-risk-high' : 
                            value.after < value.before ? 'text-risk-low' : 'text-white'
                          }`}>{value.after.toFixed(2)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* SHAP Explanation */}
                <SHAPExplanationPanel reasons={simulationResult.top_risk_factors} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Custom slider styles */}
      <style jsx global>{`
        input[type="range"].slider-thumb {
          -webkit-appearance: none;
          background: linear-gradient(to right, 
            rgb(239, 68, 68) 0%, 
            rgb(245, 158, 11) 50%, 
            rgb(34, 197, 94) 100%
          );
          height: 6px;
          border-radius: 4px;
        }
        input[type="range"].slider-thumb::-webkit-slider-thumb {
          -webkit-appearance: none;
          width: 18px;
          height: 18px;
          background: linear-gradient(135deg, #8b5cf6, #06b6d4);
          border-radius: 50%;
          cursor: pointer;
          border: 2px solid white;
          box-shadow: 0 0 10px rgba(139, 92, 246, 0.5);
        }
        input[type="range"].slider-thumb::-moz-range-thumb {
          width: 18px;
          height: 18px;
          background: linear-gradient(135deg, #8b5cf6, #06b6d4);
          border-radius: 50%;
          cursor: pointer;
          border: 2px solid white;
          box-shadow: 0 0 10px rgba(139, 92, 246, 0.5);
        }
      `}</style>
    </div>
  );
}