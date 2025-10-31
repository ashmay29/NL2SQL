import React from 'react';
import { Card } from './ui/Card';
import { Button } from './ui/Button';
import { Badge } from './ui/Badge';

interface ConversationTurn {
  query: string;
  sql: string;
  confidence: number;
  timestamp: string;
  complexity?: string;
  executionTime?: number;
}

interface ConversationHistoryProps {
  conversationId: string;
  turns: ConversationTurn[];
  onSelectTurn?: (turn: ConversationTurn) => void;
  onClearHistory?: () => void;
  maxTurns?: number;
}

export const ConversationHistory: React.FC<ConversationHistoryProps> = ({
  conversationId,
  turns,
  onSelectTurn,
  onClearHistory,
  maxTurns = 10,
}) => {
  const displayTurns = turns.slice(-maxTurns).reverse(); // Show most recent first

  const formatTimestamp = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleTimeString();
    } catch {
      return timestamp;
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getComplexityBadge = (complexity?: string) => {
    if (!complexity) return null;
    
    const variant = {
      simple: 'success',
      moderate: 'secondary',
      complex: 'warning',
      very_complex: 'error',
    }[complexity] || 'secondary';
    
    return (
      <Badge variant={variant as any} size="sm">
        {complexity}
      </Badge>
    );
  };

  return (
    <Card className="p-4">
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold">Conversation History</h3>
            <p className="text-xs text-gray-600">
              ID: <code className="bg-gray-100 px-1 rounded">{conversationId}</code>
            </p>
          </div>
          
          {onClearHistory && turns.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={onClearHistory}
            >
              Clear
            </Button>
          )}
        </div>

        {/* Turn List */}
        {displayTurns.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <div className="text-4xl mb-2">💬</div>
            <p>No conversation history yet.</p>
            <p className="text-sm">Start by asking a question!</p>
          </div>
        ) : (
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {displayTurns.map((turn, index) => (
              <div
                key={index}
                className={`border rounded-lg p-3 transition-colors ${
                  onSelectTurn 
                    ? 'cursor-pointer hover:bg-gray-50 hover:border-blue-300' 
                    : ''
                }`}
                onClick={() => onSelectTurn?.(turn)}
              >
                {/* Turn Header */}
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs text-gray-500">
                      {formatTimestamp(turn.timestamp)}
                    </span>
                    <span className={`text-xs font-medium ${getConfidenceColor(turn.confidence)}`}>
                      {Math.round(turn.confidence * 100)}%
                    </span>
                    {getComplexityBadge(turn.complexity)}
                  </div>
                  
                  {turn.executionTime && (
                    <Badge variant="secondary" size="sm">
                      {turn.executionTime.toFixed(2)}s
                    </Badge>
                  )}
                </div>

                {/* Query */}
                <div className="mb-2">
                  <div className="text-sm font-medium text-gray-700 mb-1">
                    🤔 Query:
                  </div>
                  <div className="text-sm text-gray-900 bg-blue-50 p-2 rounded">
                    {turn.query}
                  </div>
                </div>

                {/* SQL Preview */}
                <div>
                  <div className="text-sm font-medium text-gray-700 mb-1">
                    💾 SQL:
                  </div>
                  <div className="text-xs font-mono text-gray-600 bg-gray-50 p-2 rounded overflow-hidden">
                    <div className="truncate">
                      {turn.sql.replace(/\s+/g, ' ').trim()}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Footer */}
        {turns.length > maxTurns && (
          <div className="text-xs text-gray-500 text-center pt-2 border-t">
            Showing {maxTurns} of {turns.length} turns
          </div>
        )}
      </div>
    </Card>
  );
};
