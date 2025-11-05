import React, { useState } from 'react';
import { Card } from './ui/Card';
import { Button } from './ui/Button';
import { Badge } from './ui/Badge';
import Editor from '@monaco-editor/react';

interface SQLViewerProps {
  sql: string;
  params?: Record<string, any>;
  confidence?: number;
  executionTime?: number;
  onCopy?: () => void;
  onDownload?: () => void;
  onExecute?: () => void;
  isExecuting?: boolean;
}

export const SQLViewer: React.FC<SQLViewerProps> = ({
  sql,
  params,
  confidence,
  executionTime,
  onCopy,
  onDownload,
  onExecute,
  isExecuting = false,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      onCopy?.();
    } catch (err) {
      console.error('Failed to copy SQL:', err);
    }
  };

  const getConfidenceBadge = (confidence?: number) => {
    if (!confidence) return null;
    
    const percentage = Math.round(confidence * 100);
    let variant: 'success' | 'warning' | 'error' = 'success';
    
    if (percentage < 50) variant = 'error';
    else if (percentage < 80) variant = 'warning';
    
    return (
      <Badge variant={variant}>
        Confidence: {percentage}%
      </Badge>
    );
  };

  return (
    <Card className="p-6">
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <h3 className="text-lg font-semibold">Generated SQL</h3>
            {getConfidenceBadge(confidence)}
            {executionTime && (
              <Badge variant="secondary">
                {executionTime.toFixed(2)}s
              </Badge>
            )}
          </div>
          
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopy}
              disabled={!sql}
            >
              {copied ? 'Copied!' : 'Copy'}
            </Button>
            
            {onDownload && (
              <Button
                variant="outline"
                size="sm"
                onClick={onDownload}
                disabled={!sql}
              >
                Download
              </Button>
            )}
            
            {onExecute && (
              <Button
                onClick={onExecute}
                disabled={!sql || isExecuting}
                size="sm"
              >
                {isExecuting ? 'Executing...' : 'Execute'}
              </Button>
            )}
          </div>
        </div>

        {/* SQL Code */}
        {sql ? (
          <div className="relative">
            <Editor
              height="300px"
              defaultLanguage="sql"
              value={sql}
              theme="vs-light"
              options={{
                readOnly: true,
                minimap: { enabled: false },
                fontSize: 13,
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                automaticLayout: true,
                wordWrap: 'on',
                wrappingIndent: 'indent',
              }}
            />
          </div>
        ) : (
          <div className="bg-gray-50 border rounded-lg p-8 text-center text-gray-500">
            No SQL generated yet. Submit a query to see the results.
          </div>
        )}

        {/* SQL Parameters */}
        {params && Object.keys(params).length > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="text-sm font-semibold text-blue-900 mb-2">
              Query Parameters
            </h4>
            <div className="space-y-1">
              {Object.entries(params).map(([key, value]) => (
                <div key={key} className="flex items-center text-sm font-mono">
                  <span className="text-blue-700 font-semibold">{key}:</span>
                  <span className="ml-2 text-gray-700">
                    {typeof value === 'string' ? `"${value}"` : JSON.stringify(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* SQL Stats */}
        {sql && (
          <div className="text-xs text-gray-600 border-t pt-3">
            <div className="flex items-center justify-between">
              <span>Characters: {sql.length}</span>
              <span>Lines: {sql.split('\n').length}</span>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
};
