import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import { Database, Brain, TrendingUp, AlertTriangle, CheckCircle, Loader2, RefreshCw } from 'lucide-react';

interface DataInitializerProps {
  onInitComplete: () => void;
}

interface InitStatus {
  total_snapshots: number;
  pool_count: number;
  hours_of_history: number;
  latest_snapshot: string | null;
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

export default function DataInitializer({ onInitComplete }: DataInitializerProps) {
  const [status, setStatus] = useState<InitStatus | null>(null);
  const [isInitializing, setIsInitializing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(30);

  const API_URL = process.env.NEXT_PUBLIC_BACKEND_API || 'http://localhost:8001';

  const fetchStatus = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/protocols/status`);
      setStatus(res.data);
      
      // Check if init is complete
      if (res.data.init_status?.completed && res.data.data_ready) {
        setIsInitializing(false);
        onInitComplete();
      }
      
      // Check if still initializing
      if (res.data.init_status?.running) {
        setIsInitializing(true);
      }
      
      // Check for errors
      if (res.data.init_status?.error) {
        setError(res.data.init_status.error);
        setIsInitializing(false);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch status');
    }
  };

  const startInitialization = async () => {
    setError(null);
    setIsInitializing(true);
    
    try {
      await axios.post(`${API_URL}/api/protocols/initialize?days=${days}`);
    } catch (err: any) {
      setError(err.response?.data?.message || err.message || 'Failed to start initialization');
      setIsInitializing(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 2000);
    return () => clearInterval(interval);
  }, []);

  // If data is already ready, don't show the initializer
  if (status?.data_ready && status?.model_trained && !isInitializing) {
    return null;
  }

  const steps = [
    { icon: Database, label: 'Fetch Historical Data', description: 'Download 30 days of real TVL from DeFiLlama' },
    { icon: Brain, label: 'Train ML Model', description: 'Train XGBoost classifier on historical patterns' },
    { icon: TrendingUp, label: 'Run Predictions', description: 'Generate risk scores with SHAP explanations' },
    { icon: AlertTriangle, label: 'Generate Alerts', description: 'Evaluate thresholds and create alerts' },
  ];

  const currentStepIndex = status?.init_status?.progress 
    ? Math.floor((status.init_status.progress / 100) * 4)
    : 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-8 max-w-2xl mx-auto"
      data-testid="data-initializer"
    >
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-defi-primary/20 mb-4">
          <Database className="w-8 h-8 text-defi-primary" />
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">Initialize VeriRisk System</h2>
        <p className="text-gray-400">
          Fetch real DeFi protocol data and train the ML risk model
        </p>
      </div>

      {/* Status Info */}
      {status && !isInitializing && (
        <div className="grid grid-cols-2 gap-4 mb-6 p-4 bg-dark-800/50 rounded-lg">
          <div>
            <div className="text-sm text-gray-400">Snapshots</div>
            <div className="text-lg font-semibold text-white">{status.total_snapshots}</div>
          </div>
          <div>
            <div className="text-sm text-gray-400">Pools</div>
            <div className="text-lg font-semibold text-white">{status.pool_count}</div>
          </div>
          <div>
            <div className="text-sm text-gray-400">History</div>
            <div className="text-lg font-semibold text-white">{status.hours_of_history}h</div>
          </div>
          <div>
            <div className="text-sm text-gray-400">Model</div>
            <div className={`text-lg font-semibold ${status.model_trained ? 'text-risk-low' : 'text-risk-medium'}`}>
              {status.model_trained ? 'Trained' : 'Not trained'}
            </div>
          </div>
        </div>
      )}

      {/* Steps Progress */}
      <div className="space-y-3 mb-8">
        {steps.map((step, idx) => {
          const Icon = step.icon;
          const isActive = isInitializing && idx === currentStepIndex;
          const isComplete = idx < currentStepIndex || (status?.init_status?.completed && idx <= currentStepIndex);
          
          return (
            <motion.div
              key={step.label}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.1 }}
              className={`flex items-center gap-4 p-3 rounded-lg transition-colors ${
                isActive ? 'bg-defi-primary/20 border border-defi-primary/50' :
                isComplete ? 'bg-risk-low/10 border border-risk-low/30' :
                'bg-dark-800/30 border border-white/5'
              }`}
            >
              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                isActive ? 'bg-defi-primary/30' :
                isComplete ? 'bg-risk-low/30' :
                'bg-dark-700'
              }`}>
                {isActive ? (
                  <Loader2 className="w-5 h-5 text-defi-primary animate-spin" />
                ) : isComplete ? (
                  <CheckCircle className="w-5 h-5 text-risk-low" />
                ) : (
                  <Icon className="w-5 h-5 text-gray-500" />
                )}
              </div>
              <div className="flex-1">
                <div className={`font-medium ${
                  isActive ? 'text-defi-primary' :
                  isComplete ? 'text-risk-low' :
                  'text-gray-400'
                }`}>
                  {step.label}
                </div>
                <div className="text-xs text-gray-500">{step.description}</div>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Progress Bar */}
      {isInitializing && (
        <div className="mb-6">
          <div className="flex justify-between text-sm mb-2">
            <span className="text-gray-400">{status?.init_status?.phase || 'Starting...'}</span>
            <span className="text-defi-primary">{status?.init_status?.progress || 0}%</span>
          </div>
          <div className="h-2 bg-dark-700 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-defi-primary to-defi-secondary"
              initial={{ width: 0 }}
              animate={{ width: `${status?.init_status?.progress || 0}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
        </div>
      )}

      {/* Error Display */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-6 p-4 bg-risk-high/10 border border-risk-high/30 rounded-lg"
          >
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-risk-high flex-shrink-0 mt-0.5" />
              <div>
                <div className="font-medium text-risk-high">Initialization Error</div>
                <div className="text-sm text-gray-400 mt-1">{error}</div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Days Selector */}
      {!isInitializing && (
        <div className="mb-6">
          <label className="block text-sm text-gray-400 mb-2">Days of Historical Data</label>
          <select
            value={days}
            onChange={(e) => setDays(parseInt(e.target.value))}
            className="w-full px-4 py-2 bg-dark-700 border border-white/10 rounded-lg text-white focus:outline-none focus:border-defi-primary"
            data-testid="days-selector"
          >
            <option value={7}>7 days (Quick test)</option>
            <option value={14}>14 days</option>
            <option value={30}>30 days (Recommended)</option>
            <option value={60}>60 days</option>
            <option value={90}>90 days (Most comprehensive)</option>
          </select>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-4">
        {!isInitializing ? (
          <>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={startInitialization}
              className="flex-1 px-6 py-3 bg-gradient-to-r from-defi-primary to-defi-secondary text-white font-semibold rounded-lg flex items-center justify-center gap-2"
              data-testid="start-init-button"
            >
              <Database className="w-5 h-5" />
              Initialize with Real Data
            </motion.button>
            {status?.data_ready && (
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={onInitComplete}
                className="px-6 py-3 bg-dark-700 text-white font-semibold rounded-lg border border-white/10 hover:border-defi-primary/50"
                data-testid="skip-init-button"
              >
                Skip
              </motion.button>
            )}
          </>
        ) : (
          <div className="flex-1 px-6 py-3 bg-dark-700 text-gray-400 font-semibold rounded-lg flex items-center justify-center gap-2 cursor-not-allowed">
            <Loader2 className="w-5 h-5 animate-spin" />
            Initializing... This may take 2-3 minutes
          </div>
        )}
      </div>

      {/* Help Text */}
      <p className="text-xs text-gray-500 text-center mt-4">
        Data is fetched from DeFiLlama API (real historical TVL). Model training uses XGBoost with SHAP explanations.
      </p>
    </motion.div>
  );
}
