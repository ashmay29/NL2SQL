import React, { useState } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Spinner } from '../components/ui/Spinner';
import  api  from '../api/client';

interface ConnectionForm {
  host: string;
  port: number;
  username: string;
  password: string;
  database: string;
  db_type: 'mysql' | 'postgresql';
}

interface ConnectionResult {
  success: boolean;
  message: string;
  database_id: string;
  schema_summary: {
    database: string;
    tables: string[];
    table_count: number;
    total_columns: number;
    has_embeddings: boolean;
  };
}

export const DatabaseConnection: React.FC = () => {
  const [form, setForm] = useState<ConnectionForm>({
    host: 'localhost',
    port: 3306,
    username: '',
    password: '',
    database: '',
    db_type: 'mysql',
  });

  const [isLoading, setIsLoading] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [result, setResult] = useState<ConnectionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<any | null>(null);

  const handleInputChange = (field: keyof ConnectionForm, value: string | number) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setError(null);
    setResult(null);
    setTestResult(null);
  };

  const handleDbTypeChange = (type: 'mysql' | 'postgresql') => {
    setForm((prev) => ({
      ...prev,
      db_type: type,
      port: type === 'mysql' ? 3306 : 5432,
    }));
  };

  const handleTestConnection = async () => {
    setIsTesting(true);
    setError(null);
    setTestResult(null);

    try {
      const response = await api.post('/api/v1/database/test-connection', form);
      setTestResult(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Connection test failed');
    } finally {
      setIsTesting(false);
    }
  };

  const handleConnect = async () => {
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await api.post<ConnectionResult>('/api/v1/database/connect', form);
      setResult(response.data);
      
      // Store database_id in localStorage for use in queries
      if (response.data.database_id) {
        localStorage.setItem('current_database_id', response.data.database_id);
        localStorage.setItem('current_database_type', 'mysql');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to connect to database');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          Connect to Database
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Connect to your MySQL or PostgreSQL database to enable natural language queries
        </p>
      </div>

      <Card className="p-6">
        <div className="space-y-6">
          {/* Database Type Selector */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Database Type
            </label>
            <div className="flex gap-4">
              <button
                onClick={() => handleDbTypeChange('mysql')}
                className={`flex-1 py-2 px-4 rounded-lg border-2 transition-colors ${
                  form.db_type === 'mysql'
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                    : 'border-gray-300 dark:border-gray-600 hover:border-gray-400'
                }`}
              >
                MySQL
              </button>
              <button
                onClick={() => handleDbTypeChange('postgresql')}
                className={`flex-1 py-2 px-4 rounded-lg border-2 transition-colors ${
                  form.db_type === 'postgresql'
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                    : 'border-gray-300 dark:border-gray-600 hover:border-gray-400'
                }`}
              >
                PostgreSQL
              </button>
            </div>
          </div>

          {/* Connection Form */}
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2 sm:col-span-1">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Host
              </label>
              <Input
                type="text"
                value={form.host}
                onChange={(e) => handleInputChange('host', e.target.value)}
                placeholder="localhost or db.example.com"
              />
            </div>

            <div className="col-span-2 sm:col-span-1">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Port
              </label>
              <Input
                type="number"
                value={form.port}
                onChange={(e) => handleInputChange('port', parseInt(e.target.value))}
                placeholder={form.db_type === 'mysql' ? '3306' : '5432'}
              />
            </div>

            <div className="col-span-2 sm:col-span-1">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Username
              </label>
              <Input
                type="text"
                value={form.username}
                onChange={(e) => handleInputChange('username', e.target.value)}
                placeholder="database username"
              />
            </div>

            <div className="col-span-2 sm:col-span-1">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Password
              </label>
              <Input
                type="password"
                value={form.password}
                onChange={(e) => handleInputChange('password', e.target.value)}
                placeholder="database password"
              />
            </div>

            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Database Name
              </label>
              <Input
                type="text"
                value={form.database}
                onChange={(e) => handleInputChange('database', e.target.value)}
                placeholder="my_database"
              />
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-4">
            <Button
              onClick={handleTestConnection}
              disabled={isTesting || !form.database || !form.username}
              variant="secondary"
              className="flex-1"
            >
              {isTesting ? <Spinner size="sm" /> : 'Test Connection'}
            </Button>
            <Button
              onClick={handleConnect}
              disabled={isLoading || !form.database || !form.username}
              className="flex-1"
            >
              {isLoading ? <Spinner size="sm" /> : 'Connect & Extract Schema'}
            </Button>
          </div>

          {/* Test Result */}
          {testResult && (
            <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
              <div className="flex items-start gap-3">
                <svg className="w-5 h-5 text-green-600 dark:text-green-400 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <div className="flex-1">
                  <p className="text-sm font-medium text-green-800 dark:text-green-300">
                    Connection Successful!
                  </p>
                  <div className="mt-2 text-sm text-green-700 dark:text-green-400">
                    <p>Database: {testResult.database}</p>
                    <p>Tables: {testResult.table_count}</p>
                    <p className="text-xs mt-1 text-green-600 dark:text-green-500">{testResult.version}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Connection Result */}
          {result && (
            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
              <div className="flex items-start gap-3">
                <svg className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                </svg>
                <div className="flex-1">
                  <p className="text-sm font-medium text-blue-800 dark:text-blue-300">
                    {result.message}
                  </p>
                  <div className="mt-3 space-y-2">
                    <div className="p-3 bg-white dark:bg-gray-800 rounded border border-blue-200 dark:border-blue-700">
                      <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Database ID (use in queries)</p>
                      <code className="text-sm text-blue-600 dark:text-blue-400 font-mono">{result.database_id}</code>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">Tables:</span>
                        <span className="ml-2 font-medium text-gray-900 dark:text-white">{result.schema_summary.table_count}</span>
                      </div>
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">Columns:</span>
                        <span className="ml-2 font-medium text-gray-900 dark:text-white">{result.schema_summary.total_columns}</span>
                      </div>
                    </div>
                    {result.schema_summary.tables.length > 0 && (
                      <div className="mt-2">
                        <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Tables:</p>
                        <div className="flex flex-wrap gap-1">
                          {result.schema_summary.tables.slice(0, 10).map((table) => (
                            <span key={table} className="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs rounded">
                              {table}
                            </span>
                          ))}
                          {result.schema_summary.tables.length > 10 && (
                            <span className="px-2 py-0.5 text-gray-500 dark:text-gray-400 text-xs">
                              +{result.schema_summary.tables.length - 10} more
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <div className="flex items-start gap-3">
                <svg className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <div>
                  <p className="text-sm font-medium text-red-800 dark:text-red-300">
                    Connection Failed
                  </p>
                  <p className="mt-1 text-sm text-red-700 dark:text-red-400">
                    {error}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Help Text */}
          <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
              💡 Connection Tips
            </h3>
            <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1 list-disc list-inside">
              <li>Ensure your database server is accessible from this application</li>
              <li>Check that the username has SELECT permissions on the database</li>
              <li>For remote connections, verify firewall rules allow the connection</li>
              <li>The schema will be cached for 7 days for faster access</li>
              <li>After connecting, use the database_id in the NL2SQL playground</li>
            </ul>
          </div>
        </div>
      </Card>
    </div>
  );
};
