import { useState, useRef } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { useNL2IR, useIR2SQL, useNL2SQL } from '../api/hooks';
import { Sparkles, Code, Database, AlertCircle, Upload, X, FileText } from 'lucide-react';
import Editor from '@monaco-editor/react';

export const NLSQLPlayground = () => {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<'step-by-step' | 'direct'>('direct');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const nl2ir = useNL2IR();
  const ir2sql = useIR2SQL();
  const nl2sql = useNL2SQL();

  const handleStepByStep = async () => {
    if (!query.trim()) return;
    
    try {
      // Step 1: NL → IR
      const irResult = await nl2ir.mutateAsync({
        query_text: query,
        database_id: 'nl2sql_target',
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
        database_id: 'nl2sql_target',
      });
    } catch (error) {
      console.error('Direct error:', error);
    }
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Validate file type (SQL, CSV, JSON)
      const validTypes = ['.sql', '.csv', '.json', '.db'];
      const fileExt = file.name.substring(file.name.lastIndexOf('.'));
      
      if (validTypes.includes(fileExt.toLowerCase())) {
        setUploadedFile(file);
        // In production, you'd upload this to the backend
        console.log('File uploaded:', file.name);
      } else {
        alert('Please upload a valid database file (.sql, .csv, .json, .db)');
      }
    }
  };

  const removeFile = () => {
    setUploadedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const isLoading = nl2ir.isPending || ir2sql.isPending || nl2sql.isPending;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-semibold text-apple-gray-900 mb-2">Playground</h1>
        <p className="text-apple-gray-500">Convert natural language to SQL queries</p>
      </div>

      {/* Database Upload Section */}
      <Card>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-apple-gray-900">Database Source</h3>
              <p className="text-sm text-apple-gray-500">Upload your database or use our sample data</p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowUpload(!showUpload)}
            >
              <Upload className="w-4 h-4" />
              {showUpload ? 'Hide Upload' : 'Upload Database'}
            </Button>
          </div>

          {showUpload && (
            <div className="p-4 bg-apple-gray-50 rounded-xl space-y-3">
              <input
                ref={fileInputRef}
                type="file"
                accept=".sql,.csv,.json,.db"
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
                  <p className="text-sm font-medium text-apple-gray-700">Click to upload database file</p>
                  <p className="text-xs text-apple-gray-500 mt-1">Supports .sql, .csv, .json, .db files</p>
                </label>
              ) : (
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
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={removeFile}
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              )}

              <div className="flex items-start gap-2 p-3 bg-apple-blue/10 rounded-lg">
                <AlertCircle className="w-4 h-4 text-apple-blue flex-shrink-0 mt-0.5" />
                <p className="text-xs text-apple-gray-700">
                  {uploadedFile 
                    ? 'Your database has been uploaded. The system will analyze the schema and relationships automatically.'
                    : 'No file uploaded. Using sample e-commerce database with customers, orders, and products tables.'
                  }
                </p>
              </div>
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
            <Card>
              <h2 className="text-xl font-semibold text-apple-gray-900 mb-4">Generated SQL</h2>
              <Editor
                height="200px"
                defaultLanguage="sql"
                value={ir2sql.data.sql}
                theme="vs-light"
                options={{
                  readOnly: true,
                  minimap: { enabled: false },
                  fontSize: 13,
                }}
              />
              {Object.keys(ir2sql.data.params).length > 0 && (
                <div className="mt-4">
                  <p className="text-sm font-medium text-apple-gray-700 mb-2">Parameters:</p>
                  <pre className="text-xs bg-apple-gray-50 p-3 rounded-xl overflow-x-auto">
                    {JSON.stringify(ir2sql.data.params, null, 2)}
                  </pre>
                </div>
              )}
            </Card>
          )}
        </>
      )}

      {/* Results - Direct */}
      {mode === 'direct' && nl2sql.data && (
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-apple-gray-900">Generated SQL</h2>
            <div className="flex items-center gap-2">
              {nl2sql.data.cache_hit && (
                <Badge variant="info">Cached</Badge>
              )}
              <Badge variant={nl2sql.data.confidence > 0.8 ? 'success' : 'warning'}>
                Confidence: {(nl2sql.data.confidence * 100).toFixed(0)}%
              </Badge>
            </div>
          </div>

          {nl2sql.data.explanations.length > 0 && (
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
          )}

          <Editor
            height="250px"
            defaultLanguage="sql"
            value={nl2sql.data.sql}
            theme="vs-light"
            options={{
              readOnly: true,
              minimap: { enabled: false },
              fontSize: 13,
            }}
          />

          <div className="mt-4 text-sm text-apple-gray-500">
            Execution time: {nl2sql.data.execution_time.toFixed(2)}ms
          </div>
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
