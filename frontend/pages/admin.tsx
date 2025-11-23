import { useState } from 'react';
import Link from 'next/link';
import axios from 'axios';

export default function Admin() {
  const [poolId, setPoolId] = useState('test_pool_1');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_BACKEND_API || 'http://localhost:8001';

  const handleInfer = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await axios.post(`${API_URL}/infer`, {
        pool_id: poolId
      });
      setResult(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to run inference');
    } finally {
      setLoading(false);
    }
  };

  const handleInferAndSign = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await axios.post(`${API_URL}/infer_and_sign`, {
        pool_id: poolId
      });
      setResult(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to infer and sign');
    } finally {
      setLoading(false);
    }
  };

  const handlePushChain = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await axios.post(`${API_URL}/push_chain`, {
        pool_id: poolId
      });
      setResult(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to push to chain');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900">
      {/* Header */}
      <header className="bg-gray-800/50 backdrop-blur-sm border-b border-gray-700">
        <div className="container mx-auto px-4 py-6">
          <Link href="/" className="text-blue-400 hover:text-blue-300 flex items-center gap-2 mb-4">
            ← Back to Dashboard
          </Link>
          <h1 className="text-3xl font-bold text-white">Admin Panel</h1>
          <p className="text-gray-400 mt-1">Test risk inference and submission</p>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Input Card */}
        <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg border border-gray-700 p-6 mb-6">
          <h2 className="text-xl font-semibold text-white mb-4">Test Risk Computation</h2>
          
          <div className="mb-4">
            <label className="block text-gray-300 mb-2">Pool ID</label>
            <input
              type="text"
              value={poolId}
              onChange={(e) => setPoolId(e.target.value)}
              className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
              placeholder="Enter pool ID (e.g., test_pool_1)"
              data-testid="pool-id-input"
            />
            <p className="text-gray-400 text-sm mt-2">
              Available test pools: test_pool_1, test_pool_2
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button
              onClick={handleInfer}
              disabled={loading}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              data-testid="infer-button"
            >
              {loading ? '⏳' : '🧠'} Infer Only
            </button>

            <button
              onClick={handleInferAndSign}
              disabled={loading}
              className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-600 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              data-testid="infer-sign-button"
            >
              {loading ? '⏳' : '🔐'} Infer + Sign
            </button>

            <button
              onClick={handlePushChain}
              disabled={loading}
              className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              data-testid="push-chain-button"
            >
              {loading ? '⏳' : '⛓️'} Push to Chain
            </button>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-500/10 border border-red-500 rounded-lg p-4 mb-6" data-testid="error-message">
            <h3 className="text-red-400 font-semibold mb-2">Error</h3>
            <p className="text-red-300 text-sm">{error}</p>
          </div>
        )}

        {/* Result Display */}
        {result && (
          <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg border border-gray-700 p-6">
            <h2 className="text-xl font-semibold text-white mb-4">Result</h2>
            
            {result.risk_score !== undefined && (
              <div className="mb-4 p-4 bg-gray-700/50 rounded-lg">
                <div className="text-4xl font-bold text-white mb-2">
                  {result.risk_score.toFixed(1)}
                  <span className="text-xl text-gray-400">/100</span>
                </div>
                <div className="text-gray-300">Risk Level: {result.risk_level || 'N/A'}</div>
              </div>
            )}

            {result.top_reasons && (
              <div className="mb-4">
                <h3 className="text-white font-semibold mb-2">Top Risk Factors:</h3>
                <div className="space-y-2">
                  {result.top_reasons.map((reason: any, idx: number) => (
                    <div key={idx} className="flex justify-between items-center bg-gray-700/30 px-4 py-2 rounded">
                      <span className="text-gray-300 capitalize">
                        {reason.feature.replace(/_/g, ' ')}
                      </span>
                      <span className={`font-mono font-semibold ${
                        reason.impact > 0 ? 'text-red-400' : 'text-green-400'
                      }`}>
                        {reason.impact > 0 ? '+' : ''}{reason.impact.toFixed(3)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {result.signature && (
              <div className="mb-4">
                <h3 className="text-white font-semibold mb-2">Signature:</h3>
                <code className="block bg-gray-900 text-green-400 p-3 rounded text-xs overflow-x-auto">
                  {result.signature}
                </code>
              </div>
            )}

            {result.tx_hash && (
              <div className="mb-4">
                <h3 className="text-white font-semibold mb-2">Transaction:</h3>
                <a
                  href={result.explorer_url || `https://sepolia.etherscan.io/tx/${result.tx_hash}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:text-blue-300 break-all"
                >
                  {result.tx_hash}
                </a>
              </div>
            )}

            <details className="mt-4">
              <summary className="cursor-pointer text-gray-400 hover:text-gray-300">
                View Full Response JSON
              </summary>
              <pre className="mt-2 bg-gray-900 text-green-400 p-4 rounded text-xs overflow-x-auto">
                {JSON.stringify(result, null, 2)}
              </pre>
            </details>
          </div>
        )}

        {/* Info Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
          <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg border border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-white mb-3">📊 Infer Only</h3>
            <p className="text-gray-400 text-sm">
              Computes risk score with SHAP explanations. Does not sign or submit to blockchain.
              Useful for testing the ML model.
            </p>
          </div>

          <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg border border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-white mb-3">🔐 Infer + Sign</h3>
            <p className="text-gray-400 text-sm">
              Computes risk score and creates cryptographically signed payload. Does not submit to chain.
              Useful for verifying signatures.
            </p>
          </div>

          <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg border border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-white mb-3">⛓️ Push to Chain</h3>
            <p className="text-gray-400 text-sm">
              Full workflow: infer, sign, and submit to Sepolia testnet. Requires Oracle contract deployment and Sepolia ETH.
            </p>
          </div>

          <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg border border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-white mb-3">ℹ️ Backend Status</h3>
            <a 
              href={`${API_URL}/health`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-400 hover:text-blue-300 text-sm"
            >
              Check API Health →
            </a>
          </div>
        </div>
      </main>
    </div>
  );
}
