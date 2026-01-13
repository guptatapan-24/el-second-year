import { motion } from 'framer-motion';
import { Shield, AlertTriangle, HelpCircle } from 'lucide-react';

interface ConfidenceBadgeProps {
  confidence: 'HIGH' | 'MEDIUM' | 'LOW' | string;
  reason?: string;
  size?: 'sm' | 'md' | 'lg';
  showTooltip?: boolean;
}

export default function ConfidenceBadge({ 
  confidence, 
  reason,
  size = 'md',
  showTooltip = true 
}: ConfidenceBadgeProps) {
  const getConfidenceConfig = (level: string) => {
    switch (level.toUpperCase()) {
      case 'HIGH':
        return {
          bgColor: 'bg-risk-low/10',
          borderColor: 'border-risk-low/30',
          textColor: 'text-risk-low',
          glowColor: 'shadow-[0_0_15px_rgba(34,197,94,0.3)]',
          icon: Shield,
          label: 'High Confidence'
        };
      case 'MEDIUM':
        return {
          bgColor: 'bg-risk-medium/10',
          borderColor: 'border-risk-medium/30',
          textColor: 'text-risk-medium',
          glowColor: 'shadow-[0_0_15px_rgba(245,158,11,0.3)]',
          icon: AlertTriangle,
          label: 'Medium Confidence'
        };
      case 'LOW':
        return {
          bgColor: 'bg-risk-high/10',
          borderColor: 'border-risk-high/30',
          textColor: 'text-risk-high',
          glowColor: 'shadow-[0_0_15px_rgba(239,68,68,0.3)]',
          icon: HelpCircle,
          label: 'Low Confidence'
        };
      default:
        return {
          bgColor: 'bg-gray-500/10',
          borderColor: 'border-gray-500/30',
          textColor: 'text-gray-400',
          glowColor: '',
          icon: HelpCircle,
          label: 'Unknown'
        };
    }
  };

  const config = getConfidenceConfig(confidence);
  const Icon = config.icon;

  const sizeClasses = {
    sm: 'px-2 py-1 text-xs gap-1',
    md: 'px-3 py-1.5 text-sm gap-2',
    lg: 'px-4 py-2 text-base gap-2'
  };

  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-4 h-4',
    lg: 'w-5 h-5'
  };

  return (
    <div className="relative group" data-testid="confidence-badge">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        whileHover={{ scale: 1.02 }}
        className={`
          inline-flex items-center rounded-lg border
          ${config.bgColor} ${config.borderColor} ${config.textColor} ${config.glowColor}
          ${sizeClasses[size]}
          transition-all duration-300
        `}
      >
        <motion.div
          animate={{ 
            scale: [1, 1.1, 1],
          }}
          transition={{ 
            duration: 2, 
            repeat: Infinity,
            ease: 'easeInOut'
          }}
        >
          <Icon className={iconSizes[size]} />
        </motion.div>
        <span className="font-medium">{config.label}</span>
      </motion.div>

      {/* Tooltip */}
      {showTooltip && reason && (
        <div className="
          absolute bottom-full left-1/2 -translate-x-1/2 mb-2
          px-3 py-2 rounded-lg bg-dark-700 border border-white/10
          text-xs text-gray-300 whitespace-nowrap
          opacity-0 group-hover:opacity-100
          pointer-events-none
          transition-opacity duration-200
          z-50
        ">
          {reason}
          <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1">
            <div className="border-4 border-transparent border-t-dark-700" />
          </div>
        </div>
      )}
    </div>
  );
}