import { useState, useRef } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { SQLViewer } from '../components/SQLViewer';
import { useNL2IR, useIR2SQL, useNL2SQL, useUploadCSV } from '../api/hooks';
import { Sparkles, Code, Database, AlertCircle, Upload, X, FileText, CheckCircle, Server } from 'lucide-react';
import Editor from '@monaco-editor/react';
import api from '../api/client';

type DataSource = 'csv' | 'database';

export const NLSQLPlayground = () => {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<'step-by-step' | 'direct'>('direct');
  const [dataSource, setDataSource] = useState<DataSource>('csv');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [showDataSource, setShowDataSource] = useState(false);
  const [databaseId, setDatabaseId] = useState('uploaded_data');
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [tableName, setTableName] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Database connection state
  const [dbForm, setDbForm] = useState({
    host: 'localhost',
    port: 3306,
    username: '',
    password: '',
    database: '',
    db_type: 'mysql' as 'mysql' | 'postgresql',
  });
  const [isConnecting, setIsConnecting] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [dbConnected, setDbConnected] = useState(false);
  const [dbError, setDbError] = useState<string | null>(null);
  const [dbTestResult, setDbTestResult] = useState<any>(null);

  const nl2ir = useNL2IR();
  const ir2sql = useIR2SQL();
  const nl2sql = useNL2SQL();
  const uploadCSV = useUploadCSV();

  const handleStepByStep = async () => {
    if (!query.trim()) return;
    
    try {
      // Step 1: NL → IR
      const irResult = await nl2ir.mutateAsync({
        query_text: query,
        database_id: databaseId, // Use state instead of hardcoded value
      });

      // Step 2: IR → SQL
      if (irResult.ir) {
        await ir2sql.mutateAsync({ ir: irResult.ir });
      }
    } catch (error) {
      console.error('Step-by-step error:', error);
    }
  };

  const handleDirect = async () => {
    if (!query.trim()) return;
    
    try {
      await nl2sql.mutateAsync({
        query_text: query,
        database_id: databaseId, // Use state instead of hardcoded value
      });
    } catch (error) {
      console.error('Direct error:', error);
    }
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Validate file type
      const validTypes = ['.csv', '.xlsx'];
      const fileExt = file.name.substring(file.name.lastIndexOf('.'));
      
      if (validTypes.includes(fileExt.toLowerCase())) {
        setUploadedFile(file);
        // Auto-generate table name from filename
        const name = file.name.replace(/\.[^/.]+$/, '').replace(/[^a-zA-Z0-9_]/g, '_');
        setTableName(name);
        setUploadSuccess(false);
      } else {
        alert('Please upload a valid CSV or Excel file');
      }
    }
  };

  const handleUploadToBackend = async () => {
    if (!uploadedFile || !tableName.trim()) {
      alert('Please select a file and provide a table name');
      return;
    }

    try {
      const result = await uploadCSV.mutateAsync({
        file: uploadedFile,
        tableName: tableName,
      });
      
      console.log('Upload successful:', result);
      setUploadSuccess(true);
      setDatabaseId('uploaded_data'); // Ensure we use the right database ID
      
      // Show success message
      alert(`✅ File uploaded successfully!\n\nTable: ${result.table_name}\nRows: ${result.row_count}\nColumns: ${result.column_count}\n\nYou can now query your data!`);
    } catch (error: any) {
      console.error('Upload failed:', error);
      alert(`❌ Upload failed: ${error.response?.data?.detail || error.message}`);
      setUploadSuccess(false);
    }
  };

  const removeFile = () => {
    setUploadedFile(null);
    setUploadSuccess(false);
    setTableName('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Database connection handlers
  const handleDbInputChange = (field: string, value: string | number) => {
    setDbForm((prev) => ({ ...prev, [field]: value }));
    setDbError(null);
    setDbTestResult(null);
  };

  const handleDbTypeChange = (type: 'mysql' | 'postgresql') => {
    setDbForm((prev) => ({
      ...prev,
      db_type: type,
      port: type === 'mysql' ? 3306 : 5432,
    }));
  };

  const handleTestConnection = async () => {
    setIsTesting(true);
    setDbError(null);
    setDbTestResult(null);

    try {
      const response = await api.post('/api/v1/database/test-connection', dbForm);
      setDbTestResult(response.data);
    } catch (err: any) {
      setDbError(err.response?.data?.detail || 'Connection test failed');
    } finally {
      setIsTesting(false);
    }
  };

  const handleConnectDatabase = async () => {
    setIsConnecting(true);
    setDbError(null);

    try {
      const response = await api.post('/api/v1/database/connect', dbForm);
      const result = response.data;
      
      // Store database_id and mark as connected
      setDatabaseId(result.database_id);
      setDbConnected(true);
      localStorage.setItem('current_database_id', result.database_id);
      localStorage.setItem('current_database_type', 'mysql');
      
      alert(`✅ Connected to ${result.schema_summary.database}!\n\nTables: ${result.schema_summary.table_count}\nColumns: ${result.schema_summary.total_columns}\n\nYou can now query your database!`);
    } catch (err: any) {
      setDbError(err.response?.data?.detail || 'Failed to connect to database');
    } finally {
      setIsConnecting(false);
    }
  };

  const handleDisconnectDatabase = () => {
    setDbConnected(false);
    setDatabaseId('uploaded_data');
    setDbTestResult(null);
    localStorage.removeItem('current_database_id');
    localStorage.removeItem('current_database_type');
  };

  const isLoading = nl2ir.isPending || ir2sql.isPending || nl2sql.isPending || uploadCSV.isPending;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-semibold text-apple-gray-900 mb-2">Playground</h1>
        <p className="text-apple-gray-500">Convert natural language to SQL queries</p>
      </div>

      {/* Data Source Section */}
      <Card>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-apple-gray-900">Data Source</h3>
              <p className="text-sm text-apple-gray-500">Upload CSV/Excel or connect to a database</p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowDataSource(!showDataSource)}
            >
              <Database className="w-4 h-4" />
              {showDataSource ? 'Hide' : 'Configure'} Data Source
            </Button>
          </div>

          {showDataSource && (
            <div className="space-y-4">
              {/* Source Type Selector */}
              <div className="flex gap-4">
                <button
                  onClick={() => setDataSource('csv')}
                  className={`flex-1 py-3 px-4 rounded-lg border-2 transition-colors ${
                    dataSource === 'csv'
                      ? 'border-blue-500  text-blue-700 dark:text-blue-500'
                      : 'border-gray-300 dark:border-gray-600 hover:border-gray-400'
                  }`}
                >
                  <Upload className="w-5 h-5 mx-auto mb-1" />
                  <div className="text-sm font-medium">CSV / Excel</div>
                </button>
                <button
                  onClick={() => setDataSource('database')}
                  className={`flex-1 py-3 px-4 rounded-lg border-2 transition-colors ${
                    dataSource === 'database'
                      ? 'border-blue-500  text-blue-700 dark:text-blue-500'
                      : 'border-gray-300 dark:border-gray-600 hover:border-gray-400'
                  }`}
                >
                  <Server className="w-5 h-5 mx-auto mb-1" />
                  <div className="text-sm font-medium">MySQL / PostgreSQL</div>
                </button>
              </div>

              {/* CSV Upload Section */}
              {dataSource === 'csv' && (
                <div className="p-4 bg-apple-gray-50 rounded-xl space-y-3">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".sql,.csv,.json,.db,.xlsx"
                    onChange={handleFileUpload}
                    className="hidden"
                    id="file-upload"
                  />
                  
                  {!uploadedFile ? (
                    <label
                      htmlFor="file-upload"
                      className="flex flex-col items-center justify-center p-8 border-2 border-dashed border-apple-gray-300 rounded-lg cursor-pointer hover:border-apple-blue hover:bg-apple-blue/5 transition-colors"
                    >
                      <Upload className="w-8 h-8 text-apple-gray-400 mb-2" />
                      <p className="text-sm font-medium text-apple-gray-700">Click to upload file</p>
                      <p className="text-xs text-apple-gray-500 mt-1">Supports .csv and .xlsx files</p>
                    </label>
                  ) : (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between p-4 bg-white rounded-lg border border-apple-gray-200">
                        <div className="flex items-center gap-3">
                          <FileText className="w-5 h-5 text-apple-blue" />
                          <div>
                            <p className="text-sm font-medium text-apple-gray-900">{uploadedFile.name}</p>
                            <p className="text-xs text-apple-gray-500">
                              {(uploadedFile.size / 1024).toFixed(2)} KB
                            </p>
                          </div>
                        </div>
                        <Button variant="ghost" size="sm" onClick={removeFile}>
                          <X className="w-4 h-4" />
                        </Button>
                      </div>
                      
                      <Input
                        label="Table Name"
                        placeholder="e.g., customers, sales, products"
                        value={tableName}
                        onChange={(e) => setTableName(e.target.value)}
                      />
                      
                      <Button
                        onClick={handleUploadToBackend}
                        loading={uploadCSV.isPending}
                        disabled={!tableName.trim()}
                        className="w-full"
                      >
                        {uploadSuccess ? (
                          <>
                            <CheckCircle className="w-4 h-4" />
                            Uploaded Successfully
                          </>
                        ) : (
                          <>
                            <Upload className="w-4 h-4" />
                            Upload to Backend
                          </>
                        )}
                      </Button>
                    </div>
                  )}

                  <div className="flex items-start gap-2 p-3 bg-apple-blue/10 rounded-lg">
                    <AlertCircle className="w-4 h-4 text-apple-blue flex-shrink-0 mt-0.5" />
                    <p className="text-xs text-apple-gray-700">
                      {uploadSuccess
                        ? '✅ Your file has been uploaded and is ready to query!'
                        : uploadedFile 
                        ? '⚠️ File selected but not uploaded yet. Click "Upload to Backend" to proceed.'
                        : 'ℹ️ Upload a file to query your own data.'
                      }
                    </p>
                  </div>
                </div>
              )}

              {/* Database Connection Section */}
              {dataSource === 'database' && (
                <div className="p-4 bg-apple-gray-50 rounded-xl space-y-4">
                  {!dbConnected ? (
                    <>
                      {/* Database Type Selector */}
                      <div className="flex gap-3">
                        <button
                          onClick={() => handleDbTypeChange('mysql')}
                          className={`flex-1 py-2 px-3 rounded-lg border-2 text-sm transition-colors ${
                            dbForm.db_type === 'mysql'
                              ? 'border-blue-500 bg-blue-50 text-blue-700'
                              : 'border-gray-300 hover:border-gray-400'
                          }`}
                        >
                          MySQL
                        </button>
                        <button
                          onClick={() => handleDbTypeChange('postgresql')}
                          className={`flex-1 py-2 px-3 rounded-lg border-2 text-sm transition-colors ${
                            dbForm.db_type === 'postgresql'
                              ? 'border-blue-500 bg-blue-50 text-blue-700'
                              : 'border-gray-300 hover:border-gray-400'
                          }`}
                        >
                          PostgreSQL
                        </button>
                      </div>

                      {/* Connection Form */}
                      <div className="grid grid-cols-2 gap-3">
                        <Input
                          label="Host"
                          placeholder="localhost"
                          value={dbForm.host}
                          onChange={(e) => handleDbInputChange('host', e.target.value)}
                        />
                        <Input
                          label="Port"
                          type="number"
                          placeholder={dbForm.db_type === 'mysql' ? '3306' : '5432'}
                          value={dbForm.port}
                          onChange={(e) => handleDbInputChange('port', parseInt(e.target.value))}
                        />
                        <Input
                          label="Username"
                          placeholder="root"
                          value={dbForm.username}
                          onChange={(e) => handleDbInputChange('username', e.target.value)}
                        />
                        <Input
                          label="Password"
                          type="password"
                          placeholder="••••••"
                          value={dbForm.password}
                          onChange={(e) => handleDbInputChange('password', e.target.value)}
                        />
                        <div className="col-span-2">
                          <Input
                            label="Database Name"
                            placeholder="my_database"
                            value={dbForm.database}
                            onChange={(e) => handleDbInputChange('database', e.target.value)}
                          />
                        </div>
                      </div>

                      {/* Test Result */}
                      {dbTestResult && (
                        <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                          <div className="flex items-start gap-2">
                            <CheckCircle className="w-4 h-4 text-green-600 mt-0.5" />
                            <div className="flex-1 text-sm">
                              <p className="font-medium text-green-800">Connection Test Passed!</p>
                              <p className="text-green-700 text-xs mt-1">
                                {dbTestResult.table_count} tables found
                              </p>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Error Message */}
                      {dbError && (
                        <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                          <div className="flex items-start gap-2">
                            <AlertCircle className="w-4 h-4 text-red-600 mt-0.5" />
                            <div className="flex-1 text-sm">
                              <p className="font-medium text-red-800">Connection Failed</p>
                              <p className="text-red-700 text-xs mt-1">{dbError}</p>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Action Buttons */}
                      <div className="flex gap-3">
                        <Button
                          onClick={handleTestConnection}
                          loading={isTesting}
                          disabled={!dbForm.database || !dbForm.username}
                          variant="secondary"
                          size="sm"
                          className="flex-1"
                        >
                          Test Connection
                        </Button>
                        <Button
                          onClick={handleConnectDatabase}
                          loading={isConnecting}
                          disabled={!dbForm.database || !dbForm.username}
                          size="sm"
                          className="flex-1"
                        >
                          <Server className="w-4 h-4" />
                          Connect
                        </Button>
                      </div>
                    </>
                  ) : (
                    <div className="space-y-3">
                      <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                        <div className="flex items-start gap-3">
                          <CheckCircle className="w-5 h-5 text-green-600 mt-0.5" />
                          <div className="flex-1">
                            <p className="text-sm font-medium text-green-800">
                              Connected to {dbForm.database}
                            </p>
                            <p className="text-xs text-green-700 mt-1">
                              Database ID: <code className="font-mono">{databaseId}</code>
                            </p>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={handleDisconnectDatabase}
                          >
                            Disconnect
                          </Button>
                        </div>
                      </div>
                      <div className="flex items-start gap-2 p-3 bg-blue-50 rounded-lg">
                        <AlertCircle className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
                        <p className="text-xs text-blue-800">
                          ✅ Your database is connected and ready to query!
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </Card>

      {/* Query Input Section */}
      <Card>
        <div className="space-y-4">
          <Input
            label="Natural Language Query"
            placeholder="e.g., Show me the top 5 customers by total spent"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />

          <div className="flex items-center gap-3">
            <Button
              onClick={() => setMode('direct')}
              variant={mode === 'direct' ? 'primary' : 'secondary'}
              size="sm"
            >
              <Sparkles className="w-4 h-4" />
              Direct (NL → SQL)
            </Button>
            <Button
              onClick={() => setMode('step-by-step')}
              variant={mode === 'step-by-step' ? 'primary' : 'secondary'}
              size="sm"
            >
              <Code className="w-4 h-4" />
              Step-by-Step (NL → IR → SQL)
            </Button>
          </div>

          <Button
            onClick={mode === 'direct' ? handleDirect : handleStepByStep}
            loading={isLoading}
            disabled={!query.trim()}
            className="w-full"
          >
            <Database className="w-4 h-4" />
            Generate SQL
          </Button>
        </div>
      </Card>

      {/* Results - Step by Step */}
      {mode === 'step-by-step' && (
        <>
          {/* IR Result */}
          {nl2ir.data && (
            <Card>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-apple-gray-900">Intermediate Representation (IR)</h2>
                <Badge variant={nl2ir.data.confidence > 0.8 ? 'success' : 'warning'}>
                  Confidence: {(nl2ir.data.confidence * 100).toFixed(0)}%
                </Badge>
              </div>

              {nl2ir.data.questions.length > 0 && (
                <div className="mb-4 p-3 bg-apple-orange/10 border border-apple-orange/20 rounded-xl">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="w-5 h-5 text-apple-orange flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="font-medium text-apple-orange mb-1">Clarifications Needed:</p>
                      <ul className="text-sm text-apple-gray-700 space-y-1">
                        {nl2ir.data.questions.map((q, i) => (
                          <li key={i}>• {q}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              <Editor
                height="300px"
                defaultLanguage="json"
                value={JSON.stringify(nl2ir.data.ir, null, 2)}
                theme="vs-light"
                options={{
                  readOnly: true,
                  minimap: { enabled: false },
                  fontSize: 13,
                }}
              />
            </Card>
          )}

          {/* SQL Result */}
          {ir2sql.data && (
            <SQLViewer
              sql={ir2sql.data.sql}
              params={ir2sql.data.params}
            />
          )}
        </>
      )}

      {/* Results - Direct */}
      {mode === 'direct' && nl2sql.data && (
        <Card>
          {/* <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-apple-gray-900">Generated SQL</h2>
            <div className="flex items-center gap-2">
              {nl2sql.data.cache_hit && (
                <Badge variant="info">Cached</Badge>
              )}
              <Badge variant={nl2sql.data.confidence > 0.8 ? 'success' : 'warning'}>
                Confidence: {(nl2sql.data.confidence * 100).toFixed(0)}%
              </Badge>
            </div>
          </div> */}

          {/* {nl2sql.data.explanations.length > 0 && (
            <div className="mb-4 p-3 bg-apple-orange/10 border border-apple-orange/20 rounded-xl">
              <div className="flex items-start gap-2">
                <AlertCircle className="w-5 h-5 text-apple-orange flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-apple-orange mb-1">Notes:</p>
                  <ul className="text-sm text-apple-gray-700 space-y-1">
                    {nl2sql.data.explanations.map((exp, i) => (
                      <li key={i}>• {exp}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )} */}

          <SQLViewer
            sql={nl2sql.data.sql}
            params={nl2sql.data.params}
            confidence={nl2sql.data.confidence}
            executionTime={nl2sql.data.execution_time}
          />
        </Card>
      )}

      {/* Error Display */}
      {(nl2ir.error || ir2sql.error || nl2sql.error) && (
        <Card>
          <div className="p-3 bg-apple-red/10 border border-apple-red/20 rounded-xl">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-apple-red flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-apple-red mb-1">Error:</p>
                <p className="text-sm text-apple-gray-700">
                  {(nl2ir.error || ir2sql.error || nl2sql.error)?.message}
                </p>
              </div>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};
