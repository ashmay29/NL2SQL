import React, { useState } from 'react';
import { Button } from './ui/Button';
import { Input } from './ui/Input';
import { Card } from './ui/Card';
import { Spinner } from './ui/Spinner';

interface QueryInputProps {
  onSubmit: (query: string) => void;
  isLoading?: boolean;
  placeholder?: string;
  conversationId?: string;
  onConversationChange?: (id: string) => void;
}

export const QueryInput: React.FC<QueryInputProps> = ({
  onSubmit,
  isLoading = false,
  placeholder = "Ask a question about your data...",
  conversationId,
  onConversationChange,
}) => {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSubmit(query.trim());
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const generateNewConversation = () => {
    const newId = `conv-${Date.now()}`;
    onConversationChange?.(newId);
  };

  return (
    <Card className="p-6">
      <div className="space-y-4">
        {/* Conversation Controls */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-600">Conversation:</span>
            <code className="text-xs bg-gray-100 px-2 py-1 rounded">
              {conversationId || 'default'}
            </code>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={generateNewConversation}
            disabled={isLoading}
          >
            New Conversation
          </Button>
        </div>

        {/* Query Input Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="relative">
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={placeholder}
              disabled={isLoading}
              className="pr-12"
            />
            {isLoading && (
              <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                <Spinner size="sm" />
              </div>
            )}
          </div>

          <div className="flex items-center justify-between">
            <div className="text-xs text-gray-500">
              Press Enter to submit, Shift+Enter for new line
            </div>
            <Button
              type="submit"
              disabled={!query.trim() || isLoading}
              className="min-w-[100px]"
            >
              {isLoading ? <Spinner size="sm" /> : 'Ask'}
            </Button>
          </div>
        </form>

        {/* Example Queries */}
        <div className="border-t pt-4">
          <div className="text-xs text-gray-600 mb-2">Example queries:</div>
          <div className="flex flex-wrap gap-2">
            {[
              "Show all customers",
              "Top 5 products by sales",
              "Orders from last month",
              "Customer revenue by country"
            ].map((example) => (
              <button
                key={example}
                onClick={() => setQuery(example)}
                disabled={isLoading}
                className="text-xs bg-blue-50 hover:bg-blue-100 text-blue-700 px-2 py-1 rounded transition-colors disabled:opacity-50"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      </div>
    </Card>
  );
};
