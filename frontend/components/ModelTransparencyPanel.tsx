import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Brain, Clock, Database, Code, ChevronDown, ChevronUp, 
  Sparkles, Award, Layers, Info 
} from 'lucide-react';
import axios from 'axios';

interface ModelInfo {
  model_name: string;
  model_type: string;
  training_date: string;
  features_used: string[];
  auc_score: number | null;
  training_samples: number;
  last_retrained: string;
  hyperparameters: Record<string, any>;
  model_description: string;
  shap_explanation: string;
}

interface ModelTransparencyPanelProps {
  compact?: boolean;
}

export default function ModelTransparencyPanel({ compact = false }: ModelTransparencyPanelProps) {
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(!compact);
  const [error, setError] = useState<string | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_BACKEND_API || 'http://localhost:8001';

  useEffect(() => {
    const fetchModelInfo = async () => {
      try {
        const res = await axios.get(`${API_URL}/api/model/info`);
        setModelInfo(res.data);
        setLoading(false);
      } catch (err) {
        console.error('Failed to fetch model info:', err);
        setError('Unable to load model information');
        setLoading(false);
      }
    };
    fetchModelInfo();
  }, [API_URL]);

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };

  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="glass-card p-6"
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-dark-600 shimmer-loading" />
          <div className="space-y-2">
            <div className="h-4 w-32 bg-dark-600 rounded shimmer-loading" />
            <div className="h-3 w-24 bg-dark-600 rounded shimmer-loading" />
          </div>
        </div>
        <div className="space-y-3">
          <div className="h-3 w-full bg-dark-600 rounded shimmer-loading" />
          <div className="h-3 w-3/4 bg-dark-600 rounded shimmer-loading" />
        </div>
      </motion.div>
    );
  }

  if (error || !modelInfo) {
    return (
      <div className="glass-card p-6 text-center">
        <Brain className="w-8 h-8 text-gray-500 mx-auto mb-2" />
        <p className="text-gray-400 text-sm">{error || 'Model info unavailable'}</p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card overflow-hidden"
      data-testid="model-transparency-panel"
    >
      {/* Header */}
      <div 
        className={`p-6 ${compact ? 'cursor-pointer hover:bg-dark-700/30 transition-colors' : ''}`}
        onClick={() => compact && setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <motion.div 
              className="w-10 h-10 rounded-lg bg-gradient-to-br from-defi-primary/20 to-defi-secondary/20 flex items-center justify-center border border-defi-primary/30"
              whileHover={{ scale: 1.05 }}
            >
              <Brain className="w-5 h-5 text-defi-primary" />
            </motion.div>
            <div>
              <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                ML Model Details
                <span className="px-2 py-0.5 text-[10px] rounded bg-defi-primary/20 text-defi-primary font-mono">
                  {modelInfo.model_name}
                </span>
              </h3>
              <p className="text-xs text-gray-500">Transparency for examiner trust</p>
            </div>
          </div>
          {compact && (
            <motion.button
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              className="p-1 text-gray-400 hover:text-white"
            >
              {expanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
            </motion.button>
          )}
        </div>
      </div>

      {/* Content */}
      <motion.div
        initial={false}
        animate={{ height: expanded ? 'auto' : 0, opacity: expanded ? 1 : 0 }}
        transition={{ duration: 0.3, ease: 'easeInOut' }}
        className="overflow-hidden"
      >
        <div className="px-6 pb-6 space-y-5">
          {/* Model Type & AUC */}
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-dark-700/50 rounded-xl border border-white/5">
              <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
                <Layers className="w-3 h-3" />
                Model Type
              </div>
              <div className="text-white font-medium">{modelInfo.model_type}</div>
            </div>
            <div className="p-4 bg-dark-700/50 rounded-xl border border-white/5">
              <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
                <Award className="w-3 h-3" />
                AUC Score
              </div>
              <div className="text-white font-medium flex items-center gap-2">
                {modelInfo.auc_score !== null ? (
                  <>
                    <span className="text-risk-low">{modelInfo.auc_score.toFixed(3)}</span>
                    {modelInfo.auc_score >= 0.9 && (
                      <span className="text-[10px] text-risk-low bg-risk-low/20 px-1.5 py-0.5 rounded">Excellent</span>
                    )}
                  </>
                ) : (
                  <span className="text-gray-400">N/A</span>
                )}
              </div>
            </div>
          </div>

          {/* Training Info */}
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-dark-700/50 rounded-xl border border-white/5">
              <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
                <Clock className="w-3 h-3" />
                Last Trained
              </div>
              <div className="text-white text-sm">{formatDate(modelInfo.last_retrained)}</div>
            </div>
            <div className="p-4 bg-dark-700/50 rounded-xl border border-white/5">
              <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
                <Database className="w-3 h-3" />
                Training Samples
              </div>
              <div className="text-white font-medium">{modelInfo.training_samples.toLocaleString()}</div>
            </div>
          </div>

          {/* Features Used */}
          <div className="p-4 bg-dark-700/50 rounded-xl border border-white/5">
            <div className="flex items-center gap-2 text-xs text-gray-500 mb-3">
              <Sparkles className="w-3 h-3" />
              Features Used ({modelInfo.features_used.length})
            </div>
            <div className="flex flex-wrap gap-2">
              {modelInfo.features_used.slice(0, 10).map((feature) => (
                <span 
                  key={feature}
                  className="px-2 py-1 text-xs bg-dark-800 text-gray-300 rounded border border-white/5 font-mono"
                >
                  {feature}
                </span>
              ))}
              {modelInfo.features_used.length > 10 && (
                <span className="px-2 py-1 text-xs text-gray-500">
                  +{modelInfo.features_used.length - 10} more
                </span>
              )}
            </div>
          </div>

          {/* Hyperparameters */}
          <div className="p-4 bg-dark-700/50 rounded-xl border border-white/5">
            <div className="flex items-center gap-2 text-xs text-gray-500 mb-3">
              <Code className="w-3 h-3" />
              Hyperparameters
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {Object.entries(modelInfo.hyperparameters).map(([key, value]) => (
                <div key={key} className="text-center">
                  <div className="text-white font-mono text-sm">{String(value)}</div>
                  <div className="text-[10px] text-gray-500">{key}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Description */}
          <div className="p-4 bg-dark-700/50 rounded-xl border border-white/5">
            <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
              <Info className="w-3 h-3" />
              Model Description
            </div>
            <p className="text-sm text-gray-300 leading-relaxed">
              {modelInfo.model_description}
            </p>
          </div>

          {/* SHAP Explanation */}
          <div className="p-4 bg-defi-secondary/5 rounded-xl border border-defi-secondary/20">
            <div className="flex items-center gap-2 text-xs text-defi-secondary mb-2">
              <Sparkles className="w-3 h-3" />
              SHAP Explainability
            </div>
            <p className="text-sm text-gray-300 leading-relaxed">
              {modelInfo.shap_explanation}
            </p>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}