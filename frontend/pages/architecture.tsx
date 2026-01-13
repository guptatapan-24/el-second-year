import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import axios from 'axios';
import Link from 'next/link';
import {
  Database, Cpu, Brain, AlertCircle, LineChart, Server,
  ArrowRight, ArrowDown, Shield, Zap, Info, Code,
  Network, Workflow, ChevronRight, ExternalLink
} from 'lucide-react';
import ModelTransparencyPanel from '../components/ModelTransparencyPanel';

interface PipelineStage {
  stage: number;
  name: string;
  description: string;
  components: string[];
  frequency?: string;
  output?: string;
}

interface ArchitectureInfo {
  system_name: string;
  version: string;
  description: string;
  pipeline_stages: PipelineStage[];
  ml_model: {
    algorithm: string;
    task: string;
    output_interpretation: string;
    why_xgboost: string[];
  };
  explainability: {
    method: string;
    output: string;
    interpretation: string;
    why_shap: string[];
  };
  disclaimers: string[];
}

export default function ArchitecturePage() {
  const [archInfo, setArchInfo] = useState<ArchitectureInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeStage, setActiveStage] = useState<number | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_BACKEND_API || 'http://localhost:8001';

  useEffect(() => {
    const fetchArchInfo = async () => {
      try {
        const res = await axios.get(`${API_URL}/api/model/architecture`);
        setArchInfo(res.data);
      } catch (err) {
        console.error('Failed to fetch architecture info:', err);
        // Use fallback data
        setArchInfo(getDefaultArchInfo());
      } finally {
        setLoading(false);
      }
    };
    fetchArchInfo();
  }, [API_URL]);

  const getDefaultArchInfo = (): ArchitectureInfo => ({
    system_name: 'VeriRisk',
    version: '1.0.0',
    description: 'Verifiable AI Risk Oracle for DeFi Protocols',
    pipeline_stages: [
      {
        stage: 1,
        name: 'Data Ingestion',
        description: 'Fetches real-time data from DeFi protocols via APIs and on-chain sources',
        components: ['Infura RPC', 'TheGraph', 'CoinGecko API'],
        frequency: 'Every 5 minutes'
      },
      {
        stage: 2,
        name: 'Feature Engineering',
        description: 'Computes predictive features from raw protocol data',
        components: ['TVL Trends', 'Volume Analysis', 'Reserve Balance', 'Volatility Metrics'],
        output: '10 engineered features per protocol'
      },
      {
        stage: 3,
        name: 'ML Inference',
        description: 'XGBoost model predicts crash probability from features',
        components: ['XGBoost Classifier', 'SHAP Explainer'],
        output: 'Risk Score (0-100) + Top 3 Contributing Factors'
      },
      {
        stage: 4,
        name: 'Simulation Engine',
        description: 'What-if analysis by injecting hypothetical stress scenarios',
        components: ['TVL Shock', 'Volume Spike', 'Volatility Surge'],
        output: 'Simulated Risk Score + Delta Analysis'
      },
      {
        stage: 5,
        name: 'Alert System',
        description: 'Generates alerts based on risk thresholds and escalation patterns',
        components: ['High Risk Alert', 'Early Warning Alert', 'Risk Spike Alert'],
        output: 'HIGH >= 65, MEDIUM >= 30, LOW < 30'
      },
      {
        stage: 6,
        name: 'Frontend Visualization',
        description: 'Interactive dashboard for monitoring and exploration',
        components: ['Risk Gauges', 'Timeline Charts', 'SHAP Panels', 'Alert Feed']
      }
    ],
    ml_model: {
      algorithm: 'XGBoost (Gradient Boosting)',
      task: 'Binary Classification (Crash vs No-Crash)',
      output_interpretation: 'Probability * 100 = Risk Score',
      why_xgboost: [
        'Fast inference (<10ms per prediction)',
        'Handles tabular financial data well',
        'Built-in feature importance',
        'Compatible with SHAP TreeExplainer',
        'Production-proven in finance applications'
      ]
    },
    explainability: {
      method: 'SHAP (SHapley Additive exPlanations)',
      output: 'Feature-level contribution scores',
      interpretation: 'Positive SHAP = Increases Risk, Negative SHAP = Decreases Risk',
      why_shap: [
        'Consistent and accurate feature attribution',
        'Model-agnostic methodology',
        'Fast TreeExplainer for gradient boosting',
        'Research-backed (NIPS 2017 paper)'
      ]
    },
    disclaimers: [
      'This system provides early-warning risk signals, not financial advice.',
      'Predictions are probabilistic and may not capture all risk factors.',
      'Past performance does not guarantee future results.',
      'Built for academic demonstration purposes.'
    ]
  });

  const stageIcons: Record<number, React.ElementType> = {
    1: Database,
    2: Workflow,
    3: Brain,
    4: Zap,
    5: AlertCircle,
    6: LineChart
  };

  const stageColors: Record<number, string> = {
    1: 'from-blue-500 to-blue-600',
    2: 'from-purple-500 to-purple-600',
    3: 'from-defi-primary to-defi-secondary',
    4: 'from-orange-500 to-orange-600',
    5: 'from-risk-high to-red-600',
    6: 'from-green-500 to-green-600'
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-12">
        <div className="animate-pulse space-y-6">
          <div className="h-12 w-64 bg-dark-600 rounded" />
          <div className="h-6 w-96 bg-dark-600 rounded" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-48 bg-dark-600 rounded-xl" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute top-20 left-10 w-72 h-72 bg-defi-primary/10 rounded-full blur-3xl animate-pulse-slow" />
          <div className="absolute bottom-20 right-10 w-96 h-96 bg-defi-secondary/10 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }} />
        </div>

        <div className="container mx-auto px-4 py-16 relative">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="max-w-4xl"
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-defi-secondary/10 border border-defi-secondary/30 text-defi-secondary text-sm font-medium mb-6">
              <Network className="w-4 h-4" />
              System Architecture
            </div>

            <h1 className="text-4xl md:text-5xl font-bold text-white mb-4" data-testid="architecture-title">
              {archInfo?.system_name || 'VeriRisk'} <span className="text-gray-400">Architecture</span>
            </h1>
            <p className="text-xl text-gray-400 mb-6">
              {archInfo?.description || 'Verifiable AI Risk Oracle for DeFi Protocols'}
            </p>
            <div className="flex items-center gap-4 text-sm text-gray-500">
              <span className="px-3 py-1 bg-dark-700 rounded-full">Version {archInfo?.version || '1.0.0'}</span>
              <span className="flex items-center gap-1">
                <Code className="w-4 h-4" />
                XGBoost + SHAP
              </span>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Pipeline Overview */}
      <section className="container mx-auto px-4 py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <h2 className="text-2xl font-bold text-white mb-8 flex items-center gap-3">
            <Server className="w-6 h-6 text-defi-primary" />
            Data Pipeline
          </h2>

          {/* Visual Pipeline Flow */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
            {archInfo?.pipeline_stages.map((stage, idx) => {
              const Icon = stageIcons[stage.stage] || Database;
              const colorClass = stageColors[stage.stage] || 'from-gray-500 to-gray-600';
              const isActive = activeStage === stage.stage;

              return (
                <motion.div
                  key={stage.stage}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 * idx }}
                  onClick={() => setActiveStage(isActive ? null : stage.stage)}
                  className={`glass-card p-6 cursor-pointer transition-all duration-300 ${
                    isActive ? 'ring-2 ring-defi-primary scale-[1.02]' : 'hover:border-white/20'
                  }`}
                  data-testid={`pipeline-stage-${stage.stage}`}
                >
                  {/* Stage Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${colorClass} flex items-center justify-center`}>
                      <Icon className="w-6 h-6 text-white" />
                    </div>
                    <span className="text-xs font-mono text-gray-500">STAGE {stage.stage}</span>
                  </div>

                  {/* Stage Content */}
                  <h3 className="text-lg font-semibold text-white mb-2">{stage.name}</h3>
                  <p className="text-sm text-gray-400 mb-4">{stage.description}</p>

                  {/* Components */}
                  <div className="flex flex-wrap gap-2 mb-3">
                    {stage.components.map((comp) => (
                      <span
                        key={comp}
                        className="px-2 py-1 text-xs bg-dark-700 text-gray-300 rounded border border-white/5"
                      >
                        {comp}
                      </span>
                    ))}
                  </div>

                  {/* Output/Frequency */}
                  {(stage.frequency || stage.output) && (
                    <div className="pt-3 border-t border-white/5">
                      {stage.frequency && (
                        <p className="text-xs text-defi-primary">⏱ {stage.frequency}</p>
                      )}
                      {stage.output && (
                        <p className="text-xs text-defi-secondary">→ {stage.output}</p>
                      )}
                    </div>
                  )}
                </motion.div>
              );
            })}
          </div>
        </motion.div>
      </section>

      {/* Model Details Section */}
      <section className="container mx-auto px-4 py-12">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* ML Model Info */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
            className="glass-card p-6"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-defi-primary to-defi-secondary flex items-center justify-center">
                <Brain className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">ML Model</h3>
                <p className="text-xs text-gray-500">Why XGBoost?</p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <div className="text-xs text-gray-500 mb-1">Algorithm</div>
                <div className="text-white font-medium">{archInfo?.ml_model.algorithm}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500 mb-1">Task</div>
                <div className="text-white font-medium">{archInfo?.ml_model.task}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500 mb-1">Output</div>
                <div className="text-defi-primary font-mono text-sm">{archInfo?.ml_model.output_interpretation}</div>
              </div>

              <div className="pt-4 border-t border-white/10">
                <div className="text-xs text-gray-500 mb-3">Key Benefits</div>
                <ul className="space-y-2">
                  {archInfo?.ml_model.why_xgboost.map((reason, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm text-gray-300">
                      <ChevronRight className="w-4 h-4 text-risk-low mt-0.5 flex-shrink-0" />
                      {reason}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </motion.div>

          {/* SHAP Explainability Info */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4 }}
            className="glass-card p-6"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-purple-600 flex items-center justify-center">
                <Info className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">Explainability</h3>
                <p className="text-xs text-gray-500">How SHAP works</p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <div className="text-xs text-gray-500 mb-1">Method</div>
                <div className="text-white font-medium">{archInfo?.explainability.method}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500 mb-1">Output</div>
                <div className="text-white font-medium">{archInfo?.explainability.output}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500 mb-1">Interpretation</div>
                <div className="text-defi-secondary font-mono text-sm">{archInfo?.explainability.interpretation}</div>
              </div>

              <div className="pt-4 border-t border-white/10">
                <div className="text-xs text-gray-500 mb-3">Why SHAP?</div>
                <ul className="space-y-2">
                  {archInfo?.explainability.why_shap.map((reason, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm text-gray-300">
                      <ChevronRight className="w-4 h-4 text-defi-secondary mt-0.5 flex-shrink-0" />
                      {reason}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Model Transparency Panel */}
      <section className="container mx-auto px-4 py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
            <Shield className="w-6 h-6 text-defi-primary" />
            Model Transparency
          </h2>
          <ModelTransparencyPanel />
        </motion.div>
      </section>

      {/* Evaluation Ready Statements */}
      <section className="container mx-auto px-4 py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="glass-card p-6"
        >
          <h2 className="text-xl font-semibold text-white mb-6 flex items-center gap-3">
            <Shield className="w-5 h-5 text-risk-low" />
            Evaluation Ready Statements
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 bg-dark-700/50 rounded-xl border border-risk-low/20">
              <p className="text-sm text-gray-300">
                "This model uses XGBoost trained on historical DeFi protocol metrics."
              </p>
            </div>
            <div className="p-4 bg-dark-700/50 rounded-xl border border-defi-secondary/20">
              <p className="text-sm text-gray-300">
                "SHAP values explain how each feature contributes to the risk score."
              </p>
            </div>
            <div className="p-4 bg-dark-700/50 rounded-xl border border-defi-primary/20">
              <p className="text-sm text-gray-300">
                "Simulation allows users to test hypothetical stress scenarios."
              </p>
            </div>
            <div className="p-4 bg-dark-700/50 rounded-xl border border-risk-medium/20">
              <p className="text-sm text-gray-300">
                "The system provides early-warning risk signals, not financial advice."
              </p>
            </div>
          </div>
        </motion.div>
      </section>

      {/* Disclaimers */}
      <section className="container mx-auto px-4 py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="glass-card p-6 border-risk-medium/20"
        >
          <h2 className="text-lg font-semibold text-risk-medium mb-4 flex items-center gap-2">
            <AlertCircle className="w-5 h-5" />
            Important Disclaimers
          </h2>
          <ul className="space-y-3">
            {archInfo?.disclaimers.map((disclaimer, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm text-gray-400">
                <span className="text-risk-medium">•</span>
                {disclaimer}
              </li>
            ))}
          </ul>
        </motion.div>
      </section>

      {/* Quick Links */}
      <section className="container mx-auto px-4 py-12">
        <div className="flex flex-wrap justify-center gap-4">
          <Link href="/protocols">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="px-6 py-3 bg-defi-primary text-white rounded-lg flex items-center gap-2"
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
              className="px-6 py-3 bg-dark-700 text-white rounded-lg flex items-center gap-2 border border-white/10"
            >
              <Zap className="w-5 h-5" />
              Try Simulation
            </motion.button>
          </Link>
        </div>
      </section>
    </div>
  );
}