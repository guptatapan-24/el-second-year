import { motion } from 'framer-motion';

interface LoadingSkeletonProps {
  type?: 'card' | 'stat' | 'chart' | 'text' | 'gauge';
  count?: number;
}

export default function LoadingSkeleton({ type = 'card', count = 1 }: LoadingSkeletonProps) {
  const items = Array.from({ length: count });

  const CardSkeleton = () => (
    <div className="glass-card p-6 space-y-4">
      <div className="flex justify-between items-start">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-dark-600 shimmer-loading" />
          <div className="space-y-2">
            <div className="h-4 w-24 bg-dark-600 rounded shimmer-loading" />
            <div className="h-3 w-16 bg-dark-600 rounded shimmer-loading" />
          </div>
        </div>
        <div className="h-6 w-16 bg-dark-600 rounded-full shimmer-loading" />
      </div>
      <div className="h-32 w-full bg-dark-600 rounded-lg shimmer-loading" />
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <div className="h-3 w-12 bg-dark-600 rounded shimmer-loading" />
          <div className="h-5 w-20 bg-dark-600 rounded shimmer-loading" />
        </div>
        <div className="space-y-2">
          <div className="h-3 w-12 bg-dark-600 rounded shimmer-loading" />
          <div className="h-5 w-20 bg-dark-600 rounded shimmer-loading" />
        </div>
      </div>
    </div>
  );

  const StatSkeleton = () => (
    <div className="glass-card p-6">
      <div className="h-4 w-24 bg-dark-600 rounded shimmer-loading mb-3" />
      <div className="h-8 w-32 bg-dark-600 rounded shimmer-loading" />
    </div>
  );

  const ChartSkeleton = () => (
    <div className="glass-card p-6">
      <div className="h-5 w-32 bg-dark-600 rounded shimmer-loading mb-4" />
      <div className="h-64 w-full bg-dark-600 rounded-lg shimmer-loading" />
    </div>
  );

  const TextSkeleton = () => (
    <div className="space-y-2">
      <div className="h-4 w-full bg-dark-600 rounded shimmer-loading" />
      <div className="h-4 w-3/4 bg-dark-600 rounded shimmer-loading" />
    </div>
  );

  const GaugeSkeleton = () => (
    <div className="flex flex-col items-center">
      <div className="w-48 h-24 bg-dark-600 rounded-t-full shimmer-loading" />
      <div className="h-8 w-20 bg-dark-600 rounded shimmer-loading mt-4" />
    </div>
  );

  const SkeletonComponent = {
    card: CardSkeleton,
    stat: StatSkeleton,
    chart: ChartSkeleton,
    text: TextSkeleton,
    gauge: GaugeSkeleton,
  }[type];

  return (
    <>
      {items.map((_, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: i * 0.1 }}
        >
          <SkeletonComponent />
        </motion.div>
      ))}
    </>
  );
}
