import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { SchemaExplorer } from './pages/SchemaExplorer';
import { NLSQLPlayground } from './pages/NLSQLPlayground';
import { EmbeddingsManager } from './pages/EmbeddingsManager';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/schema" element={<SchemaExplorer />} />
            <Route path="/playground" element={<NLSQLPlayground />} />
            <Route path="/embeddings" element={<EmbeddingsManager />} />
          </Routes>
        </Layout>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
