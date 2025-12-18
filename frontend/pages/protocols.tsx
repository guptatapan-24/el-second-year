import { useState, useEffect } from 'react';
import Link from 'next/link';
import axios from 'axios';
import ProtocolCard from '../components/ProtocolCard';
import ProtocolFilter from '../components/ProtocolFilter';
import StatsOverview from '../components/StatsOverview';

interface Protocol {
  pool_id: string;
  protocol: string;
  category: string;
  tvl: number;
  volume_24h: number;
  last_update: string;
  asset?: string;
  data_source?: string;
}

interface RiskData {
  pool_id: string;
  risk_score: number;
}

export default function Protocols() {
  const [protocols, setProtocols] = useState<Protocol[]>([]);
  const [risks, setRisks] = useState<Map<string, number>>(new Map());
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [selectedProtocol, setSelectedProtocol] = useState('All');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [isFetching, setIsFetching] = useState(false);

  const API_URL = process.env.NEXT_PUBLIC_BACKEND_API || 'http://localhost:8001';

  const fetchProtocols = async () => {
    try {
      const [protocolsRes, risksRes] = await Promise.all([
        axios.get(`${API_URL}/protocols`),
        axios.get(`${API_URL}/submissions`)
      ]);
      
      setProtocols(protocolsRes.data);
      
      // Create risk map
      const riskMap = new Map<string, number>();
      risksRes.data.forEach((submission: RiskData) => {
        if (!riskMap.has(submission.pool_id)) {
          riskMap.set(submission.pool_id, submission.risk_score);
        }
      });
      setRisks(riskMap);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching protocols:', error);
      setLoading(false);
    }
  };

  const handleFetchProtocols = async () => {
    setIsFetching(true);
    try {
      await axios.post(`${API_URL}/fetch_protocols`);
      await fetchProtocols();
    } catch (error) {
      console.error('Error fetching protocols:', error);
    } finally {
      setIsFetching(false);
    }
  };

  useEffect(() => {
    fetchProtocols();
    
    if (autoRefresh) {
      const interval = setInterval(fetchProtocols, 30000); // 30 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  // Filter protocols
  const filteredProtocols = protocols.filter(p => {
    if (selectedCategory !== 'All' && p.category !== selectedCategory) return false;
    if (selectedProtocol !== 'All' && p.protocol !== selectedProtocol) return false;
    return true;
  });

  // Calculate stats
  const totalTVL = filteredProtocols.reduce((sum, p) => sum + p.tvl, 0);
  const totalVolume = filteredProtocols.reduce((sum, p) => sum + p.volume_24h, 0);
  const avgRisk = filteredProtocols.length > 0
    ? filteredProtocols.reduce((sum, p) => sum + (risks.get(p.pool_id) || 0), 0) / filteredProtocols.length
    : 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900">
      {/* Header */}
      <header className="bg-gray-800/50 backdrop-blur-sm border-b border-gray-700 sticky top-0 z-10">
        <div className="container mx-auto px-4 py-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                <span className="text-4xl">🛡️</span>
                VeriRisk Oracle - Multi-Protocol Dashboard
              </h1>
              <p className="text-gray-400 mt-1">Real-time AI Risk Monitoring across DeFi Protocols</p>
            </div>
            <nav className="flex gap-4">
              <Link href="/" className="px-4 py-2 text-white bg-gray-700 rounded-lg hover:bg-gray-600">
                Legacy View
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
          <h2 className="text-2xl font-bold text-white">DeFi Protocol Risk Monitor</h2>
          <div className="flex gap-4 items-center">
            <label className="flex items-center gap-2 text-white">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="w-4 h-4"
              />
              Auto-refresh (30s)
            </label>
            <button
              onClick={fetchProtocols}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
              data-testid="refresh-button"
            >
              🔄 Refresh
            </button>
            <button
              onClick={handleFetchProtocols}
              disabled={isFetching}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed flex items-center gap-2"
              data-testid="fetch-protocols-button"
            >
              {isFetching ? '⏳ Fetching...' : '📡 Fetch All Protocols'}
            </button>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-white"></div>
            <p className="text-white mt-4">Loading protocols...</p>
          </div>
        ) : (
          <>
            {/* Stats Overview */}
            <StatsOverview
              totalProtocols={filteredProtocols.length}
              totalTVL={totalTVL}
              totalVolume={totalVolume}
              avgRisk={avgRisk}
            />

            {/* Filters */}
            <ProtocolFilter
              selectedCategory={selectedCategory}
              onCategoryChange={setSelectedCategory}
              selectedProtocol={selectedProtocol}
              onProtocolChange={setSelectedProtocol}
            />

            {/* Protocol Grid */}
            {filteredProtocols.length === 0 ? (
              <div className="text-center py-12 bg-gray-800/50 rounded-lg border border-gray-700">
                <p className="text-gray-400 text-lg">No protocols found</p>
                <p className="text-gray-500 mt-2">Try adjusting your filters or fetch protocol data</p>
                <button
                  onClick={handleFetchProtocols}
                  disabled={isFetching}
                  className="mt-4 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-600"
                >
                  {isFetching ? '⏳ Fetching...' : '📡 Fetch Protocol Data'}
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredProtocols.map((protocol) => (
                  <ProtocolCard
                    key={protocol.pool_id}
                    pool_id={protocol.pool_id}
                    protocol={protocol.protocol}
                    category={protocol.category}
                    tvl={protocol.tvl}
                    volume_24h={protocol.volume_24h}
                    risk_score={risks.get(protocol.pool_id)}
                    last_update={protocol.last_update}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-gray-800/50 border-t border-gray-700 mt-12">
        <div className="container mx-auto px-4 py-6 text-center text-gray-400">
          <p>VeriRisk - Multi-Protocol AI Risk Oracle • Monitoring {protocols.length} DeFi Protocols</p>
        </div>
      </footer>
    </div>
  );
}
