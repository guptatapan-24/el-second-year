interface ProtocolFilterProps {
  selectedCategory: string;
  onCategoryChange: (category: string) => void;
  selectedProtocol: string;
  onProtocolChange: (protocol: string) => void;
}

const categories = ['All', 'DEX', 'Lending', 'Other'];
const protocols = ['All', 'Uniswap V2', 'Uniswap V3', 'Aave V3', 'Compound V2', 'Curve'];

export default function ProtocolFilter({
  selectedCategory,
  onCategoryChange,
  selectedProtocol,
  onProtocolChange
}: ProtocolFilterProps) {
  return (
    <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg border border-gray-700 p-6 mb-6">
      <h3 className="text-white font-semibold mb-4">Filter Protocols</h3>
      
      {/* Category Filter */}
      <div className="mb-4">
        <label className="text-sm text-gray-400 mb-2 block">Category</label>
        <div className="flex flex-wrap gap-2">
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => onCategoryChange(cat)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                selectedCategory === cat
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
              data-testid={`filter-category-${cat.toLowerCase()}`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Protocol Filter */}
      <div>
        <label className="text-sm text-gray-400 mb-2 block">Protocol</label>
        <div className="flex flex-wrap gap-2">
          {protocols.map(proto => (
            <button
              key={proto}
              onClick={() => onProtocolChange(proto)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                selectedProtocol === proto
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
              data-testid={`filter-protocol-${proto.toLowerCase().replace(/\s/g, '-')}`}
            >
              {proto}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
