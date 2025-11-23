interface RiskBadgeProps {
  score: number;
}

export default function RiskBadge({ score }: RiskBadgeProps) {
  const getRiskLevel = (score: number) => {
    if (score < 30) return { label: 'LOW', color: 'bg-green-500', text: 'text-green-400' };
    if (score < 65) return { label: 'MEDIUM', color: 'bg-yellow-500', text: 'text-yellow-400' };
    return { label: 'HIGH', color: 'bg-red-500', text: 'text-red-400' };
  };

  const risk = getRiskLevel(score);

  return (
    <div className={`px-3 py-1 rounded-full ${risk.color}/20 ${risk.text} text-xs font-bold flex items-center gap-2`}>
      <span className={`w-2 h-2 rounded-full ${risk.color} animate-pulse`}></span>
      {risk.label}
    </div>
  );
}
