import { useEffect, useRef, useState } from 'react';
import { motion, useInView } from 'framer-motion';

interface RiskGaugeAnimatedProps {
  score: number;
  size?: number;
  showLabel?: boolean;
  animate?: boolean;
}

export default function RiskGaugeAnimated({
  score,
  size = 200,
  showLabel = true,
  animate = true,
}: RiskGaugeAnimatedProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(containerRef, { once: true });
  const [animatedScore, setAnimatedScore] = useState(animate ? 0 : score);

  // Animate score on view
  useEffect(() => {
    if (!isInView || !animate) return;

    const duration = 1500;
    const startTime = Date.now();

    const animateScore = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setAnimatedScore(eased * score);

      if (progress < 1) {
        requestAnimationFrame(animateScore);
      }
    };

    requestAnimationFrame(animateScore);
  }, [score, isInView, animate]);

  // Draw gauge
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, size, size);

    const centerX = size / 2;
    const centerY = size * 0.65;
    const radius = size * 0.4;
    const lineWidth = size * 0.06;

    // Draw background arc
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, Math.PI, 2 * Math.PI, false);
    ctx.lineWidth = lineWidth;
    ctx.strokeStyle = 'rgba(55, 65, 81, 0.5)';
    ctx.lineCap = 'round';
    ctx.stroke();

    // Draw colored segments with gradient
    const segments = [
      { start: 0, end: 30, color: '#22c55e' },
      { start: 30, end: 65, color: '#f59e0b' },
      { start: 65, end: 100, color: '#ef4444' },
    ];

    segments.forEach((segment) => {
      const startAngle = Math.PI + (segment.start / 100) * Math.PI;
      const endAngle = Math.PI + (segment.end / 100) * Math.PI;

      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, startAngle, endAngle, false);
      ctx.lineWidth = lineWidth;
      ctx.strokeStyle = segment.color;
      ctx.lineCap = 'round';
      ctx.stroke();
    });

    // Draw needle
    const needleAngle = Math.PI + (animatedScore / 100) * Math.PI;
    const needleLength = radius * 0.8;

    ctx.save();
    ctx.translate(centerX, centerY);
    ctx.rotate(needleAngle);

    // Needle glow
    ctx.shadowColor = 'rgba(255, 255, 255, 0.5)';
    ctx.shadowBlur = 10;

    // Needle shape
    ctx.beginPath();
    ctx.moveTo(-3, 0);
    ctx.lineTo(needleLength - 5, -2);
    ctx.lineTo(needleLength, 0);
    ctx.lineTo(needleLength - 5, 2);
    ctx.closePath();
    ctx.fillStyle = '#ffffff';
    ctx.fill();

    ctx.restore();

    // Center dot
    ctx.beginPath();
    ctx.arc(centerX, centerY, size * 0.04, 0, 2 * Math.PI);
    ctx.fillStyle = '#ffffff';
    ctx.shadowColor = 'rgba(255, 255, 255, 0.8)';
    ctx.shadowBlur = 10;
    ctx.fill();

    // Tick marks
    ctx.shadowBlur = 0;
    for (let i = 0; i <= 100; i += 10) {
      const angle = Math.PI + (i / 100) * Math.PI;
      const innerRadius = radius - lineWidth / 2 - 8;
      const outerRadius = radius - lineWidth / 2 - (i % 50 === 0 ? 16 : 12);

      const x1 = centerX + Math.cos(angle) * innerRadius;
      const y1 = centerY + Math.sin(angle) * innerRadius;
      const x2 = centerX + Math.cos(angle) * outerRadius;
      const y2 = centerY + Math.sin(angle) * outerRadius;

      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = 'rgba(156, 163, 175, 0.5)';
      ctx.lineWidth = i % 50 === 0 ? 2 : 1;
      ctx.stroke();
    }
  }, [animatedScore, size]);

  const getRiskLevel = (s: number) => {
    if (s < 30) return { label: 'LOW RISK', color: 'text-risk-low', glow: 'shadow-glow-green' };
    if (s < 65) return { label: 'MEDIUM RISK', color: 'text-risk-medium', glow: 'shadow-glow-yellow' };
    return { label: 'HIGH RISK', color: 'text-risk-high', glow: 'shadow-glow-red' };
  };

  const riskLevel = getRiskLevel(animatedScore);

  return (
    <motion.div
      ref={containerRef}
      className="flex flex-col items-center"
      initial={{ opacity: 0, scale: 0.9 }}
      animate={isInView ? { opacity: 1, scale: 1 } : {}}
      transition={{ duration: 0.5 }}
      data-testid="risk-gauge-animated"
    >
      <canvas
        ref={canvasRef}
        width={size}
        height={size}
        style={{ width: size, height: size }}
        className="drop-shadow-lg"
      />
      {showLabel && (
        <div className="text-center -mt-6">
          <motion.div
            className={`text-4xl font-bold ${riskLevel.color}`}
            key={Math.round(animatedScore)}
            initial={{ scale: 1.1 }}
            animate={{ scale: 1 }}
            data-testid="gauge-score"
          >
            {animatedScore.toFixed(1)}
          </motion.div>
          <div className={`text-sm font-semibold ${riskLevel.color} mt-1`}>
            {riskLevel.label}
          </div>
        </div>
      )}
    </motion.div>
  );
}
