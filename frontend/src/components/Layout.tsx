import { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Home, Database, Sparkles, Upload } from 'lucide-react';

interface LayoutProps {
  children: ReactNode;
}

const navItems = [
  { path: '/', icon: Home, label: 'Dashboard' },
  { path: '/schema', icon: Database, label: 'Schema' },
  { path: '/playground', icon: Sparkles, label: 'NL → SQL' },
  { path: '/embeddings', icon: Upload, label: 'Embeddings' },
];

export const Layout = ({ children }: LayoutProps) => {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-apple-gray-50">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 h-full w-64 bg-white border-r border-apple-gray-200 p-6">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-apple-gray-900">NL2SQL</h1>
          <p className="text-sm text-apple-gray-500 mt-1">Phase 1 & 2</p>
        </div>

        <nav className="space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;

            return (
              <Link key={item.path} to={item.path}>
                <motion.div
                  whileHover={{ x: 4 }}
                  className={`
                    flex items-center gap-3 px-4 py-3 rounded-xl transition-colors
                    ${isActive
                      ? 'bg-apple-blue text-white'
                      : 'text-apple-gray-700 hover:bg-apple-gray-100'
                    }
                  `}
                >
                  <Icon className="w-5 h-5" />
                  <span className="font-medium">{item.label}</span>
                </motion.div>
              </Link>
            );
          })}
        </nav>

        <div className="absolute bottom-6 left-6 right-6">
          <div className="p-4 bg-apple-gray-50 rounded-xl">
            <p className="text-xs text-apple-gray-500">
              Built with React, TypeScript, and TailwindCSS
            </p>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="ml-64 p-8">
        <div className="max-w-7xl mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
};
