import { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface HealthStatus {
  status: string;
  timestamp: string;
  services: Record<string, string>;
}

function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchHealth();
  }, []);

  const fetchHealth = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/health`);
      setHealth(response.data);
    } catch (error) {
      console.error('Health check failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ 
      fontFamily: 'system-ui, -apple-system, sans-serif',
      maxWidth: '800px',
      margin: '0 auto',
      padding: '40px 20px'
    }}>
      <h1 style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>
        NL2SQL System
      </h1>
      <p style={{ color: '#666', marginBottom: '2rem' }}>
        Advanced Natural Language to SQL with GNN Schema Linking
      </p>

      <div style={{
        background: '#f5f5f5',
        padding: '20px',
        borderRadius: '8px',
        marginBottom: '2rem'
      }}>
        <h2 style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>
          System Status
        </h2>
        {loading ? (
          <p>Loading...</p>
        ) : health ? (
          <div>
            <p>
              <strong>Status:</strong>{' '}
              <span style={{ 
                color: health.status === 'healthy' ? 'green' : 'orange',
                fontWeight: 'bold'
              }}>
                {health.status.toUpperCase()}
              </span>
            </p>
            <p><strong>Timestamp:</strong> {new Date(health.timestamp).toLocaleString()}</p>
          </div>
        ) : (
          <p style={{ color: 'red' }}>Failed to connect to backend</p>
        )}
      </div>

      <div style={{
        background: '#fff',
        border: '1px solid #ddd',
        padding: '20px',
        borderRadius: '8px'
      }}>
        <h2 style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>
          Quick Links
        </h2>
        <ul style={{ lineHeight: '2' }}>
          <li>
            <a href={`${API_BASE_URL}/docs`} target="_blank" rel="noopener noreferrer">
              API Documentation (Swagger)
            </a>
          </li>
          <li>
            <a href={`${API_BASE_URL}/redoc`} target="_blank" rel="noopener noreferrer">
              API Documentation (ReDoc)
            </a>
          </li>
          <li>
            <a href={`${API_BASE_URL}/health/detailed`} target="_blank" rel="noopener noreferrer">
              Detailed Health Check
            </a>
          </li>
        </ul>
      </div>

      <div style={{ marginTop: '2rem', fontSize: '0.875rem', color: '#666' }}>
        <p><strong>Next Steps:</strong></p>
        <ul style={{ lineHeight: '1.8' }}>
          <li>✅ Backend API running with FastAPI</li>
          <li>✅ Schema service with MySQL support</li>
          <li>✅ Cache service with embeddings</li>
          <li>✅ LLM service (Ollama + Gemini)</li>
          <li>🚧 Chat interface (coming soon)</li>
          <li>🚧 Monaco SQL editor (coming soon)</li>
          <li>🚧 Query history (coming soon)</li>
        </ul>
      </div>
    </div>
  );
}

export default App;
