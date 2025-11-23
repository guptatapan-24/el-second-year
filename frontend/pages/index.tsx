import { useState, useEffect } from 'react';
import Link from 'next/link';
import axios from 'axios';
import RiskBadge from '../components/RiskBadge';
import { formatDistanceToNow } from 'date-fns';

interface PoolRisk {
  pool_id: string;
  risk_score: number;
  timestamp: string;
  status: string;
}

export default function Home() {
  const [pools, setPools] = useState<PoolRisk[]>([]);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const API_URL = process.env.NEXT_PUBLIC_BACKEND_API || 'http://localhost:8001';

  const fetchPools = async () => {
    try {
      const response = await axios.get(`${API_URL}/submissions`);
      
      // Group by pool_id and get latest for each
      const poolMap = new Map<string, PoolRisk>();
      response.data.forEach((submission: any) => {
        if (!poolMap.has(submission.pool_id) || 
            new Date(submission.timestamp) > new Date(poolMap.get(submission.pool_id)!.timestamp)) {
          poolMap.set(submission.pool_id, submission);
        }
      });
      
      setPools(Array.from(poolMap.values()));
      setLoading(false);
    } catch (error) {
      console.error('Error fetching pools:', error);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPools();
    
    if (autoRefresh) {
      const interval = setInterval(fetchPools, 10000); // Refresh every 10 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900">
      {/* Header */}
      <header className="bg-gray-800/50 backdrop-blur-sm border-b border-gray-700">
        <div className="container mx-auto px-4 py-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                <span className="text-4xl">🛡️</span>
                VeriRisk Oracle
              </h1>
              <p className="text-gray-400 mt-1">Verifiable AI Risk Monitoring for DeFi Protocols</p>
            </div>
            <nav className="flex gap-4">
              <Link href="/" className="px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700">
                Dashboard
              </Link>
              <Link href="/protocols" className="px-4 py-2 text-white bg-purple-600 rounded-lg hover:bg-purple-700">
                🌐 Multi-Protocol
              </Link>
              <Link href="/admin" className="px-4 py-2 text-white bg-gray-700 rounded-lg hover:bg-gray-600">
                Admin
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {/* Controls */}
        <div className="mb-6 flex justify-between items-center">
          <h2 className="text-2xl font-bold text-white">Monitored Pools</h2>
          <div className="flex gap-4 items-center">
            <label className="flex items-center gap-2 text-white">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="w-4 h-4"
              />
              Auto-refresh (10s)
            </label>
            <button
              onClick={fetchPools}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
              data-testid="refresh-button"
            >
              🔄 Refresh
            </button>
          </div>
        </div>

        {/* Pool Grid */}
        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-white"></div>
            <p className="text-white mt-4">Loading pools...</p>
          </div>
        ) : pools.length === 0 ? (
          <div className="text-center py-12 bg-gray-800/50 rounded-lg border border-gray-700">
            <p className="text-gray-400 text-lg">No pools monitored yet</p>
            <p className="text-gray-500 mt-2">Submit risk data to see pools appear here</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {pools.map((pool) => (
              <Link
                key={pool.pool_id}
                href={`/pool/${encodeURIComponent(pool.pool_id)}`}
                className="block"
              >
                <div 
                  className="bg-gray-800/50 backdrop-blur-sm rounded-lg border border-gray-700 p-6 hover:border-blue-500 transition-all hover:shadow-lg hover:shadow-blue-500/20"
                  data-testid={`pool-card-${pool.pool_id}`}
                >
                  <div className="flex justify-between items-start mb-4">
                    <h3 className="text-lg font-semibold text-white truncate" title={pool.pool_id}>
                      {pool.pool_id}
                    </h3>
                    <RiskBadge score={pool.risk_score} />
                  </div>

                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">Risk Score</span>
                      <span className="text-white font-mono font-semibold">
                        {pool.risk_score.toFixed(1)}/100
                      </span>
                    </div>

                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">Last Update</span>
                      <span className="text-gray-300">
                        {formatDistanceToNow(new Date(pool.timestamp), { addSuffix: true })}
                      </span>
                    </div>

                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">Status</span>
                      <span className={`px-2 py-1 rounded text-xs font-semibold ${
                        pool.status === 'confirmed' ? 'bg-green-500/20 text-green-400' :
                        pool.status === 'pending' ? 'bg-yellow-500/20 text-yellow-400' :
                        'bg-red-500/20 text-red-400'
                      }`}>
                        {pool.status.toUpperCase()}
                      </span>
                    </div>
                  </div>

                  <div className="mt-4 pt-4 border-t border-gray-700">
                    <span className="text-blue-400 text-sm hover:text-blue-300 flex items-center gap-1">
                      View Details →
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-gray-800/50 border-t border-gray-700 mt-12">
        <div className="container mx-auto px-4 py-6 text-center text-gray-400">
          <p>VeriRisk - Verifiable AI Risk Oracle for DeFi • Built with XGBoost + SHAP + Ethereum</p>
        </div>
      </footer>
    </div>
  );
}
