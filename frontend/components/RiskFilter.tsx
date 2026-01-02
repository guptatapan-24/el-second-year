import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Filter, X, ChevronDown } from 'lucide-react';

interface RiskFilterProps {
  selectedRiskLevel: string;
  onRiskLevelChange: (level: string) => void;
  selectedCategory: string;
  onCategoryChange: (category: string) => void;
  selectedProtocol: string;
  onProtocolChange: (protocol: string) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  protocols?: string[];
}

const riskLevels = [
  { value: 'All', label: 'All Risks', color: 'bg-gray-600' },
  { value: 'LOW', label: 'Low Risk', color: 'bg-risk-low' },
  { value: 'MEDIUM', label: 'Medium Risk', color: 'bg-risk-medium' },
  { value: 'HIGH', label: 'High Risk', color: 'bg-risk-high' },
];

const categories = ['All', 'DEX', 'Lending', 'Yield', 'Other'];
const defaultProtocols = ['All', 'Uniswap V2', 'Uniswap V3', 'Aave V3', 'Compound V2', 'Curve'];

export default function RiskFilter({
  selectedRiskLevel,
  onRiskLevelChange,
  selectedCategory,
  onCategoryChange,
  selectedProtocol,
  onProtocolChange,
  searchQuery,
  onSearchChange,
  protocols = defaultProtocols,
}: RiskFilterProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const activeFilters = useMemo(() => {
    let count = 0;
    if (selectedRiskLevel !== 'All') count++;
    if (selectedCategory !== 'All') count++;
    if (selectedProtocol !== 'All') count++;
    if (searchQuery) count++;
    return count;
  }, [selectedRiskLevel, selectedCategory, selectedProtocol, searchQuery]);

  const clearFilters = () => {
    onRiskLevelChange('All');
    onCategoryChange('All');
    onProtocolChange('All');
    onSearchChange('');
  };

  return (
    <div className="glass-card p-4 mb-6" data-testid="risk-filter">
      {/* Main row */}
      <div className="flex flex-col md:flex-row gap-4">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search protocols..."
            className="w-full pl-10 pr-4 py-2.5 bg-dark-700 border border-white/5 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-defi-primary/50 transition-colors"
            data-testid="search-input"
          />
        </div>

        {/* Risk Level Quick Filters */}
        <div className="flex gap-2">
          {riskLevels.map((level) => (
            <motion.button
              key={level.value}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onRiskLevelChange(level.value)}
              className={`px-4 py-2.5 rounded-lg text-sm font-medium flex items-center gap-2 transition-all ${
                selectedRiskLevel === level.value
                  ? 'bg-defi-primary text-white'
                  : 'bg-dark-700 text-gray-400 hover:text-white hover:bg-dark-600'
              }`}
              data-testid={`filter-risk-${level.value.toLowerCase()}`}
            >
              <div className={`w-2 h-2 rounded-full ${level.color}`} />
              <span className="hidden sm:inline">{level.label}</span>
              <span className="sm:hidden">{level.value === 'All' ? 'All' : level.value[0]}</span>
            </motion.button>
          ))}
        </div>

        {/* Expand button */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
            isExpanded || activeFilters > 0
              ? 'bg-defi-secondary/10 text-defi-secondary border border-defi-secondary/30'
              : 'bg-dark-700 text-gray-400 hover:text-white'
          }`}
        >
          <Filter className="w-4 h-4" />
          <span>Filters</span>
          {activeFilters > 0 && (
            <span className="px-1.5 py-0.5 text-[10px] rounded-full bg-defi-secondary text-white">
              {activeFilters}
            </span>
          )}
          <ChevronDown className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {/* Expanded filters */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="pt-4 mt-4 border-t border-white/5 grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Category filter */}
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider mb-2 block">
                  Category
                </label>
                <div className="flex flex-wrap gap-2">
                  {categories.map((cat) => (
                    <button
                      key={cat}
                      onClick={() => onCategoryChange(cat)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                        selectedCategory === cat
                          ? 'bg-defi-primary text-white'
                          : 'bg-dark-700 text-gray-400 hover:text-white hover:bg-dark-600'
                      }`}
                      data-testid={`filter-category-${cat.toLowerCase()}`}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              </div>

              {/* Protocol filter */}
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider mb-2 block">
                  Protocol
                </label>
                <div className="flex flex-wrap gap-2">
                  {protocols.map((proto) => (
                    <button
                      key={proto}
                      onClick={() => onProtocolChange(proto)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                        selectedProtocol === proto
                          ? 'bg-defi-secondary text-white'
                          : 'bg-dark-700 text-gray-400 hover:text-white hover:bg-dark-600'
                      }`}
                      data-testid={`filter-protocol-${proto.toLowerCase().replace(/\s/g, '-')}`}
                    >
                      {proto}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Clear filters */}
            {activeFilters > 0 && (
              <div className="pt-4 mt-4 border-t border-white/5">
                <button
                  onClick={clearFilters}
                  className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-400 hover:text-white transition-colors"
                >
                  <X className="w-4 h-4" />
                  Clear all filters
                </button>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
