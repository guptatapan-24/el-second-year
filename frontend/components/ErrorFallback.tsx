import { motion } from 'framer-motion';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorFallbackProps {
  error?: string;
  onRetry?: () => void;
}

export default function ErrorFallback({ error = 'Something went wrong', onRetry }: ErrorFallbackProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="glass-card p-8 text-center"
    >
      <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-risk-high/10 mb-4">
        <AlertCircle className="w-8 h-8 text-risk-high" />
      </div>
      <h3 className="text-lg font-semibold text-white mb-2">Error Loading Data</h3>
      <p className="text-gray-400 text-sm mb-6 max-w-md mx-auto">{error}</p>
      {onRetry && (
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onRetry}
          className="inline-flex items-center gap-2 px-6 py-3 bg-defi-primary text-white rounded-lg font-medium hover:bg-defi-primary/90 transition-colors"
          data-testid="retry-button"
        >
          <RefreshCw className="w-4 h-4" />
          Try Again
        </motion.button>
      )}
    </motion.div>
  );
}
