import { useEffect, useRef } from 'react';

interface RiskGaugeProps {
  score: number;
  size?: number;
  showLabel?: boolean;
}

export default function RiskGauge({ score, size = 200, showLabel = true }: RiskGaugeProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, size, size);

    // Center point
    const centerX = size / 2;
    const centerY = size * 0.75;
    const radius = size * 0.35;

    // Draw background arc
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, Math.PI, 2 * Math.PI, false);
    ctx.lineWidth = size * 0.08;
    ctx.strokeStyle = '#374151';
    ctx.stroke();

    // Draw colored segments
    const segments = [
      { start: 0, end: 30, color: '#10b981' },   // Green (LOW)
      { start: 30, end: 65, color: '#f59e0b' },  // Yellow (MEDIUM)
      { start: 65, end: 100, color: '#ef4444' }, // Red (HIGH)
    ];

    segments.forEach(segment => {
      const startAngle = Math.PI + (segment.start / 100) * Math.PI;
      const endAngle = Math.PI + (segment.end / 100) * Math.PI;

      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, startAngle, endAngle, false);
      ctx.lineWidth = size * 0.08;
      ctx.strokeStyle = segment.color;
      ctx.stroke();
    });

    // Draw needle
    const needleAngle = Math.PI + (score / 100) * Math.PI;
    const needleLength = radius * 0.85;

    ctx.save();
    ctx.translate(centerX, centerY);
    ctx.rotate(needleAngle);

    // Needle shadow
    ctx.shadowColor = 'rgba(0, 0, 0, 0.3)';
    ctx.shadowBlur = 5;
    ctx.shadowOffsetX = 2;
    ctx.shadowOffsetY = 2;

    // Needle
    ctx.beginPath();
    ctx.moveTo(-5, 0);
    ctx.lineTo(needleLength, 0);
    ctx.lineTo(needleLength - 10, -3);
    ctx.lineTo(needleLength - 10, 3);
    ctx.lineTo(needleLength, 0);
    ctx.fillStyle = '#ffffff';
    ctx.fill();

    ctx.restore();

    // Draw center circle
    ctx.beginPath();
    ctx.arc(centerX, centerY, size * 0.05, 0, 2 * Math.PI);
    ctx.fillStyle = '#ffffff';
    ctx.fill();
    ctx.strokeStyle = '#1f2937';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Draw tick marks
    for (let i = 0; i <= 100; i += 10) {
      const angle = Math.PI + (i / 100) * Math.PI;
      const outerRadius = radius + size * 0.04;
      const innerRadius = radius - size * 0.04;

      const x1 = centerX + Math.cos(angle) * innerRadius;
      const y1 = centerY + Math.sin(angle) * innerRadius;
      const x2 = centerX + Math.cos(angle) * outerRadius;
      const y2 = centerY + Math.sin(angle) * outerRadius;

      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = '#9ca3af';
      ctx.lineWidth = i % 50 === 0 ? 3 : 1;
      ctx.stroke();
    }

  }, [score, size]);

  const getRiskLevel = (score: number) => {
    if (score < 30) return { label: 'LOW RISK', color: 'text-green-400' };
    if (score < 65) return { label: 'MEDIUM RISK', color: 'text-yellow-400' };
    return { label: 'HIGH RISK', color: 'text-red-400' };
  };

  const riskLevel = getRiskLevel(score);

  return (
    <div className="flex flex-col items-center" data-testid="risk-gauge">
      <canvas 
        ref={canvasRef} 
        width={size} 
        height={size}
        className="drop-shadow-lg"
      />
      {showLabel && (
        <div className="text-center -mt-8">
          <div className={`text-4xl font-bold ${riskLevel.color}`} data-testid="gauge-score">
            {score.toFixed(1)}
          </div>
          <div className={`text-sm font-semibold ${riskLevel.color} mt-1`}>
            {riskLevel.label}
          </div>
        </div>
      )}
    </div>
  );
}
