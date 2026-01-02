import { ReactNode, useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Activity, AlertTriangle, Zap, Menu, X, RefreshCw } from 'lucide-react';
import axios from 'axios';

interface LayoutProps {
  children: ReactNode;
}

const navItems = [
  { href: '/', label: 'Dashboard', icon: Activity },
  { href: '/protocols', label: 'Protocols', icon: Shield },
  { href: '/alerts', label: 'Alerts', icon: AlertTriangle },
  { href: '/simulation', label: 'Simulation', icon: Zap },
];

export default function Layout({ children }: LayoutProps) {
  const router = useRouter();
  const [systemStatus, setSystemStatus] = useState<any>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const API_URL = process.env.NEXT_PUBLIC_BACKEND_API || 'http://localhost:8001';

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await axios.get(`${API_URL}/health`);
        setSystemStatus(res.data);
      } catch (e) {
        setSystemStatus(null);
      }
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const isActive = (href: string) => {
    if (href === '/') return router.pathname === '/';
    return router.pathname.startsWith(href);
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Navigation */}
      <header className="sticky top-0 z-50 glass-card border-b border-white/5">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-3 group">
              <motion.div
                className="w-10 h-10 rounded-lg bg-gradient-to-br from-defi-primary to-defi-secondary flex items-center justify-center"
                whileHover={{ scale: 1.05, rotate: 5 }}
                whileTap={{ scale: 0.95 }}
              >
                <Shield className="w-6 h-6 text-white" />
              </motion.div>
              <div>
                <h1 className="text-xl font-bold text-white group-hover:text-defi-primary transition-colors">
                  VeriRisk
                </h1>
                <p className="text-xs text-gray-500">AI Risk Oracle</p>
              </div>
            </Link>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center gap-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.href);
                return (
                  <Link key={item.href} href={item.href}>
                    <motion.div
                      className={`relative px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
                        active
                          ? 'text-defi-primary'
                          : 'text-gray-400 hover:text-white'
                      }`}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      {active && (
                        <motion.div
                          layoutId="nav-indicator"
                          className="absolute inset-0 bg-defi-primary/10 border border-defi-primary/30 rounded-lg"
                          transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                        />
                      )}
                      <Icon className="w-4 h-4 relative z-10" />
                      <span className="text-sm font-medium relative z-10" data-testid={`nav-${item.label.toLowerCase()}`}>
                        {item.label}
                      </span>
                    </motion.div>
                  </Link>
                );
              })}
            </nav>

            {/* Status Indicator */}
            <div className="hidden md:flex items-center gap-4">
              {/* Auto-refresh toggle */}
              <button
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  autoRefresh
                    ? 'bg-defi-primary/10 text-defi-primary border border-defi-primary/30'
                    : 'bg-dark-700 text-gray-400 border border-white/5'
                }`}
                data-testid="auto-refresh-toggle"
              >
                <RefreshCw className={`w-3 h-3 ${autoRefresh ? 'animate-spin' : ''}`} style={{ animationDuration: '3s' }} />
                Auto-refresh
              </button>

              {/* System Status */}
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-dark-700/50 border border-white/5">
                <div className="relative">
                  <div className={`w-2 h-2 rounded-full ${
                    systemStatus?.status === 'healthy' ? 'bg-risk-low' : 'bg-risk-high'
                  }`} />
                  {systemStatus?.status === 'healthy' && (
                    <div className="absolute inset-0 w-2 h-2 rounded-full bg-risk-low pulse-ring" />
                  )}
                </div>
                <span className="text-xs text-gray-400">
                  {systemStatus?.status === 'healthy' ? 'System Online' : 'Checking...'}
                </span>
              </div>
            </div>

            {/* Mobile Menu Button */}
            <button
              className="md:hidden p-2 text-gray-400 hover:text-white"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        <AnimatePresence>
          {mobileMenuOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="md:hidden border-t border-white/5"
            >
              <nav className="container mx-auto px-4 py-4 flex flex-col gap-2">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const active = isActive(item.href);
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={() => setMobileMenuOpen(false)}
                      className={`flex items-center gap-3 px-4 py-3 rounded-lg ${
                        active
                          ? 'bg-defi-primary/10 text-defi-primary border border-defi-primary/30'
                          : 'text-gray-400 hover:text-white hover:bg-dark-700'
                      }`}
                    >
                      <Icon className="w-5 h-5" />
                      <span className="font-medium">{item.label}</span>
                    </Link>
                  );
                })}
              </nav>
            </motion.div>
          )}
        </AnimatePresence>
      </header>

      {/* Main Content */}
      <main className="flex-1">
        <AnimatePresence mode="wait">
          <motion.div
            key={router.pathname}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            {children}
          </motion.div>
        </AnimatePresence>
      </main>

      {/* Footer */}
      <footer className="glass-card border-t border-white/5 mt-auto">
        <div className="container mx-auto px-4 py-6">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <div className="flex items-center gap-2 text-gray-500 text-sm">
              <Shield className="w-4 h-4" />
              <span>VeriRisk • Verifiable AI Risk Oracle for DeFi</span>
            </div>
            <div className="flex items-center gap-4 text-xs text-gray-600">
              <span>Powered by XGBoost + SHAP</span>
              <span>•</span>
              <span>Built for Academic Demonstration</span>
            </div>
          </div>
        </div>
      </footer>

      {/* Risk Color Legend (Fixed) */}
      <div className="fixed bottom-4 right-4 z-40 hidden lg:block">
        <div className="glass-card p-3 text-xs">
          <div className="text-gray-500 mb-2 font-medium">Risk Legend</div>
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-risk-low" />
              <span className="text-gray-400">Low (&lt;30)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-risk-medium" />
              <span className="text-gray-400">Medium (30-65)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-risk-high" />
              <span className="text-gray-400">High (&gt;65)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
