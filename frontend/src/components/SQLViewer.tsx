import React, { useState } from 'react';
import { Card } from './ui/Card';
import { Button } from './ui/Button';
import { Badge } from './ui/Badge';

interface SQLViewerProps {
  sql: string;
  confidence?: number;
  executionTime?: number;
  onCopy?: () => void;
  onDownload?: () => void;
  onExecute?: () => void;
  isExecuting?: boolean;
}

export const SQLViewer: React.FC<SQLViewerProps> = ({
  sql,
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

  const formatSQL = (sql: string) => {
    // Simple SQL formatting - in production, use a proper SQL formatter
    return sql
      .replace(/\bSELECT\b/gi, '\nSELECT')
      .replace(/\bFROM\b/gi, '\nFROM')
      .replace(/\bWHERE\b/gi, '\nWHERE')
      .replace(/\bJOIN\b/gi, '\n  JOIN')
      .replace(/\bLEFT JOIN\b/gi, '\n  LEFT JOIN')
      .replace(/\bINNER JOIN\b/gi, '\n  INNER JOIN')
      .replace(/\bGROUP BY\b/gi, '\nGROUP BY')
      .replace(/\bHAVING\b/gi, '\nHAVING')
      .replace(/\bORDER BY\b/gi, '\nORDER BY')
      .replace(/\bLIMIT\b/gi, '\nLIMIT')
      .trim();
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
            <pre className="bg-gray-50 border rounded-lg p-4 overflow-x-auto text-sm font-mono">
              <code className="language-sql">{formatSQL(sql)}</code>
            </pre>
            
            {/* Syntax highlighting overlay could be added here */}
          </div>
        ) : (
          <div className="bg-gray-50 border rounded-lg p-8 text-center text-gray-500">
            No SQL generated yet. Submit a query to see the results.
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
