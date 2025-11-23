import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import axios from 'axios';
import RiskBadge from '../../components/RiskBadge';
import RiskGauge from '../../components/RiskGauge';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { formatDistanceToNow, format } from 'date-fns';

interface Submission {
  pool_id: string;
  risk_score: number;
  timestamp: string;
  tx_hash: string;
  status: string;
  top_reasons: Array<{ feature: string; impact: number }>;
}

export default function PoolDetail() {
  const router = useRouter();
  const { id } = router.query;
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [latest, setLatest] = useState<Submission | null>(null);
  const [loading, setLoading] = useState(true);

  const API_URL = process.env.NEXT_PUBLIC_BACKEND_API || 'http://localhost:8001';

  useEffect(() => {
    if (id) {
      fetchPoolData();
    }
  }, [id]);

  const fetchPoolData = async () => {
    try {
      const response = await axios.get(`${API_URL}/submissions`, {
        params: { pool_id: id }
      });
      
      const sorted = response.data.sort((a: Submission, b: Submission) => 
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      );
      
      setSubmissions(sorted);
      if (sorted.length > 0) {
        setLatest(sorted[0]);
      }
      setLoading(false);
    } catch (error) {
      console.error('Error fetching pool data:', error);
      setLoading(false);
    }
  };

  const riskChartData = submissions.slice(0, 20).reverse().map(s => ({
    time: format(new Date(s.timestamp), 'HH:mm'),
    score: s.risk_score,
    fullTime: s.timestamp
  }));

  const explanationData = latest?.top_reasons?.map(r => ({
    feature: r.feature.replace(/_/g, ' '),
    impact: Math.abs(r.impact),
    rawImpact: r.impact
  })) || [];

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-white"></div>
          <p className="text-white mt-4">Loading pool data...</p>
        </div>
      </div>
    );
  }

  if (!latest) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900">
        <div className="container mx-auto px-4 py-12 text-center">
          <p className="text-white text-xl">Pool not found</p>
          <Link href="/" className="text-blue-400 hover:text-blue-300 mt-4 inline-block">
            ← Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900">
      {/* Header */}
      <header className="bg-gray-800/50 backdrop-blur-sm border-b border-gray-700">
        <div className="container mx-auto px-4 py-6">
          <Link href="/" className="text-blue-400 hover:text-blue-300 flex items-center gap-2 mb-4">
            ← Back to Dashboard
          </Link>
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-3xl font-bold text-white" data-testid="pool-title">
                {id}
              </h1>
              <p className="text-gray-400 mt-1">Pool Risk Analysis</p>
            </div>
            <RiskBadge score={latest.risk_score} />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Current Risk Score */}
          <div className="lg:col-span-2 space-y-6">
            {/* Score Card */}
            <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg border border-gray-700 p-6">
              <h2 className="text-xl font-semibold text-white mb-4">Current Risk Assessment</h2>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-6xl font-bold text-white" data-testid="risk-score">
                    {latest.risk_score.toFixed(1)}
                    <span className="text-2xl text-gray-400">/100</span>
                  </div>
                  <p className="text-gray-400 mt-2">
                    Updated {formatDistanceToNow(new Date(latest.timestamp), { addSuffix: true })}
                  </p>
                </div>
                <div className="text-right">
                  <div className={`text-sm px-3 py-1 rounded ${
                    latest.status === 'confirmed' ? 'bg-green-500/20 text-green-400' :
                    latest.status === 'pending' ? 'bg-yellow-500/20 text-yellow-400' :
                    'bg-red-500/20 text-red-400'
                  }`}>
                    {latest.status.toUpperCase()}
                  </div>
                  {latest.tx_hash && (
                    <a
                      href={`https://sepolia.etherscan.io/tx/${latest.tx_hash}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-400 hover:text-blue-300 text-sm mt-2 inline-block"
                    >
                      View on Explorer ↗
                    </a>
                  )}
                </div>
              </div>
            </div>

            {/* Risk History Chart */}
            <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg border border-gray-700 p-6">
              <h2 className="text-xl font-semibold text-white mb-4">Risk Score History</h2>
              {riskChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={riskChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="time" stroke="#9ca3af" />
                    <YAxis domain={[0, 100]} stroke="#9ca3af" />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }}
                      labelStyle={{ color: '#fff' }}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="score" 
                      stroke="#3b82f6" 
                      strokeWidth={2}
                      dot={{ fill: '#3b82f6' }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-gray-400 text-center py-8">Not enough data for chart</p>
              )}
            </div>
          </div>

          {/* Explanation Panel */}
          <div className="space-y-6">
            {/* Top Risk Factors */}
            <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg border border-gray-700 p-6">
              <h2 className="text-xl font-semibold text-white mb-4">Top Risk Factors</h2>
              {explanationData.length > 0 ? (
                <div className="space-y-4">
                  {explanationData.map((item, idx) => (
                    <div key={idx} className="border-l-4 border-blue-500 pl-4">
                      <div className="flex justify-between items-start mb-1">
                        <span className="text-white font-medium capitalize">
                          {item.feature}
                        </span>
                        <span className={`text-sm font-mono ${
                          item.rawImpact > 0 ? 'text-red-400' : 'text-green-400'
                        }`}>
                          {item.rawImpact > 0 ? '+' : ''}{item.rawImpact.toFixed(2)}
                        </span>
                      </div>
                      <div className="w-full bg-gray-700 rounded-full h-2">
                        <div 
                          className="bg-blue-500 h-2 rounded-full"
                          style={{ width: `${Math.min(item.impact * 10, 100)}%` }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-400">No explanation data available</p>
              )}
            </div>

            {/* Info Panel */}
            <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg border border-gray-700 p-6">
              <h2 className="text-xl font-semibold text-white mb-4">Pool Information</h2>
              <div className="space-y-3 text-sm">
                <div>
                  <span className="text-gray-400">Pool ID:</span>
                  <p className="text-white break-all font-mono text-xs mt-1">{id}</p>
                </div>
                <div>
                  <span className="text-gray-400">Total Submissions:</span>
                  <p className="text-white font-semibold">{submissions.length}</p>
                </div>
                <div>
                  <span className="text-gray-400">Model Version:</span>
                  <p className="text-white font-mono">xgb_v1</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Submission History */}
        <div className="mt-8 bg-gray-800/50 backdrop-blur-sm rounded-lg border border-gray-700 p-6">
          <h2 className="text-xl font-semibold text-white mb-4">Submission History</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-gray-700">
                <tr className="text-gray-400">
                  <th className="text-left py-3 px-4">Timestamp</th>
                  <th className="text-left py-3 px-4">Risk Score</th>
                  <th className="text-left py-3 px-4">Status</th>
                  <th className="text-left py-3 px-4">Transaction</th>
                </tr>
              </thead>
              <tbody>
                {submissions.slice(0, 10).map((sub, idx) => (
                  <tr key={idx} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                    <td className="py-3 px-4 text-gray-300">
                      {format(new Date(sub.timestamp), 'PPpp')}
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-mono font-semibold text-white">
                        {sub.risk_score.toFixed(1)}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-1 rounded text-xs ${
                        sub.status === 'confirmed' ? 'bg-green-500/20 text-green-400' :
                        sub.status === 'pending' ? 'bg-yellow-500/20 text-yellow-400' :
                        'bg-red-500/20 text-red-400'
                      }`}>
                        {sub.status}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      {sub.tx_hash ? (
                        <a
                          href={`https://sepolia.etherscan.io/tx/${sub.tx_hash}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-400 hover:text-blue-300 font-mono text-xs"
                        >
                          {sub.tx_hash.substring(0, 10)}...{sub.tx_hash.substring(sub.tx_hash.length - 8)}
                        </a>
                      ) : (
                        <span className="text-gray-500">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}
