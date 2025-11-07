import React from 'react';
import { NL2SQLProvider, useNL2SQL } from '../contexts/NL2SQLContext';
import { QueryInput } from '../components/QueryInput';
import { SQLViewer } from '../components/SQLViewer';
import { ComplexityBadge } from '../components/ComplexityBadge';
import { ClarificationPanel } from '../components/ClarificationPanel';
import { FeedbackForm } from '../components/FeedbackForm';
import { ConversationHistory } from '../components/ConversationHistory';
import { ResultsTable } from '../components/ResultsTable';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { useNL2SQLQuery, useSubmitFeedback } from '../api/hooks';

const PlaygroundContent: React.FC = () => {
  const {
    state,
    setConversationId,
    setCurrentQuery,
    setResponse,
    addToHistory,
    clearHistory,
    showFeedbackForm,
    showClarificationPanel,
    setQueryResults,
  } = useNL2SQL();

  const nl2sqlMutation = useNL2SQLQuery();
  const feedbackMutation = useSubmitFeedback();

  const handleQuerySubmit = async (query: string) => {
    setCurrentQuery(query);
    
    try {
      const response = await nl2sqlMutation.mutateAsync({
        query_text: query,
        conversation_id: state.conversationId,
        use_cache: true,
      });
      
      setResponse(response);
      
      // Add to history if we got SQL
      if (response.sql) {
        addToHistory({
          query,
          sql: response.sql,
          confidence: response.confidence,
          timestamp: new Date().toISOString(),
          complexity: extractComplexityFromExplanations(response.explanations),
          executionTime: response.execution_time,
          response,
        });
      }
    } catch (error) {
      console.error('Query failed:', error);
    }
  };

  const handleClarificationAnswer = async (answers: Record<string, string>) => {
    // In a real implementation, you'd send the clarification answers back to the API
    // For now, we'll just hide the clarification panel
    showClarificationPanel(false);
    
    // You could also re-submit the query with clarification context
    const clarifiedQuery = `${state.currentQuery} (Clarification: ${JSON.stringify(answers)})`;
    handleQuerySubmit(clarifiedQuery);
  };

  const handleFeedbackSubmit = async (feedback: {
    correctedSQL: string;
    reason: string;
    rating: number;
  }) => {
    if (!state.currentResponse) return;
    
    try {
      await feedbackMutation.mutateAsync({
        query_text: state.currentQuery,
        generated_sql: state.currentResponse.sql,
        corrected_sql: feedback.correctedSQL,
        schema_fingerprint: 'default', // Would come from schema service
        tables_used: extractTablesFromSQL(state.currentResponse.sql),
        metadata: {
          reason: feedback.reason,
          rating: feedback.rating,
        },
      });
      
      showFeedbackForm(false);
    } catch (error) {
      console.error('Feedback submission failed:', error);
    }
  };

  const handleConversationChange = (newId: string) => {
    setConversationId(newId);
  };

  const handleExecuteSQL = async () => {
    if (!state.currentResponse?.sql) return;
    
    setQueryResults({ isLoading: true, error: undefined });
    
    // Mock execution - in real app, call SQL execution API
    setTimeout(() => {
      setQueryResults({
        isLoading: false,
        data: [
          { id: 1, name: 'John Doe', email: 'john@example.com', total_orders: 5 },
          { id: 2, name: 'Jane Smith', email: 'jane@example.com', total_orders: 3 },
          { id: 3, name: 'Bob Johnson', email: 'bob@example.com', total_orders: 8 },
        ],
        columns: ['id', 'name', 'email', 'total_orders'],
        totalRows: 3,
      });
    }, 1500);
  };

  const extractComplexityFromExplanations = (explanations: string[]): string | undefined => {
    const complexityNote = explanations.find(exp => exp.includes('Performance note:'));
    if (complexityNote?.includes('simple')) return 'simple';
    if (complexityNote?.includes('moderate')) return 'moderate';
    if (complexityNote?.includes('complex')) return 'complex';
    return undefined;
  };

  const extractTablesFromSQL = (sql: string): string[] => {
    // Simple regex to extract table names - in production, use proper SQL parser
    const matches = sql.match(/FROM\s+(\w+)|JOIN\s+(\w+)/gi);
    if (!matches) return [];
    
    return matches
      .map(match => match.replace(/FROM\s+|JOIN\s+/gi, '').trim())
      .filter((table, index, arr) => arr.indexOf(table) === index);
  };

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-bold text-gray-900">
          NL2SQL Playground
        </h1>
        <p className="text-gray-600">
          Ask questions about your data in natural language and get SQL queries with AI assistance
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Input and History */}
        <div className="lg:col-span-1 space-y-6">
          {/* Query Input */}
          <QueryInput
            onSubmit={handleQuerySubmit}
            isLoading={nl2sqlMutation.isPending}
            conversationId={state.conversationId}
            onConversationChange={handleConversationChange}
          />

          {/* Conversation History */}
          <ConversationHistory
            conversationId={state.conversationId}
            turns={state.conversationHistory}
            onClearHistory={clearHistory}
            onSelectTurn={(turn) => {
              setCurrentQuery(turn.query);
              const maybeResponse = (turn as any).response;
              if (maybeResponse) {
                setResponse(maybeResponse);
              }
            }}
          />
        </div>

        {/* Right Column - Results */}
        <div className="lg:col-span-2 space-y-6">
          {/* Current Query Status */}
          {state.currentQuery && (
            <Card className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold">Current Query</h3>
                  <p className="text-sm text-gray-600 mt-1">{state.currentQuery}</p>
                </div>
                
                {state.currentResponse && (
                  <div className="flex items-center space-x-2">
                    <Badge variant="secondary">
                      {Math.round(state.currentResponse.confidence * 100)}% confidence
                    </Badge>
                    
                    {extractComplexityFromExplanations(state.currentResponse.explanations) && (
                      <ComplexityBadge
                        level={extractComplexityFromExplanations(state.currentResponse.explanations) as any}
                        warnings={state.currentResponse.suggested_fixes}
                      />
                    )}
                    
                    <Badge variant="secondary">
                      {state.currentResponse.execution_time.toFixed(2)}s
                    </Badge>
                  </div>
                )}
              </div>
            </Card>
          )}

          {/* Clarification Panel */}
          {state.showClarificationPanel && state.currentResponse && (
            <ClarificationPanel
              questions={state.currentResponse.explanations}
              onAnswer={handleClarificationAnswer}
              onSkip={() => showClarificationPanel(false)}
              isLoading={nl2sqlMutation.isPending}
            />
          )}

          {/* SQL Viewer */}
          {state.currentResponse && (
            <SQLViewer
              sql={state.currentResponse.sql}
              params={state.currentResponse.params}
              confidence={state.currentResponse.confidence}
              executionTime={state.currentResponse.execution_time}
              onExecute={handleExecuteSQL}
              isExecuting={state.queryResults.isLoading}
            />
          )}

          {/* Explanations and Suggestions */}
          {state.currentResponse && (state.currentResponse.explanations.length > 0 || state.currentResponse.suggested_fixes.length > 0) && (
            <Card className="p-4">
              <div className="space-y-4">
                {state.currentResponse.explanations.length > 0 && (
                  <div>
                    <h4 className="font-semibold text-blue-900 mb-2">💡 Explanations</h4>
                    <ul className="space-y-1">
                      {state.currentResponse.explanations.map((explanation, index) => (
                        <li key={index} className="text-sm text-blue-800 bg-blue-50 p-2 rounded">
                          {explanation}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                
                {state.currentResponse.suggested_fixes.length > 0 && (
                  <div>
                    <h4 className="font-semibold text-orange-900 mb-2">🔧 Suggestions</h4>
                    <ul className="space-y-1">
                      {state.currentResponse.suggested_fixes.map((fix, index) => (
                        <li key={index} className="text-sm text-orange-800 bg-orange-50 p-2 rounded">
                          {fix}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </Card>
          )}

          {/* Results Table */}
          <ResultsTable
            data={state.queryResults.data}
            columns={state.queryResults.columns}
            isLoading={state.queryResults.isLoading}
            error={state.queryResults.error}
            totalRows={state.queryResults.totalRows}
            onExport={(format) => {
              console.log(`Exporting as ${format}:`, state.queryResults.data);
            }}
          />

          {/* Feedback Form */}
          {state.showFeedbackForm && state.currentResponse && (
            <FeedbackForm
              originalQuery={state.currentQuery}
              generatedSQL={state.currentResponse.sql}
              onSubmit={handleFeedbackSubmit}
              onCancel={() => showFeedbackForm(false)}
              isSubmitting={feedbackMutation.isPending}
            />
          )}

          {/* Action Buttons */}
          {state.currentResponse?.sql && (
            <Card className="p-4">
              <div className="flex items-center justify-center space-x-4">
                <Button
                  variant="outline"
                  onClick={() => showFeedbackForm(true)}
                  disabled={state.showFeedbackForm}
                >
                  📝 Provide Feedback
                </Button>
                
                <Button
                  variant="outline"
                  onClick={() => {
                    navigator.clipboard.writeText(state.currentResponse!.sql);
                  }}
                >
                  📋 Copy SQL
                </Button>
                
                <Button
                  variant="outline"
                  onClick={() => {
                    const blob = new Blob([state.currentResponse!.sql], { type: 'text/sql' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'query.sql';
                    a.click();
                  }}
                >
                  💾 Download SQL
                </Button>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

export const NL2SQLPlaygroundEnhanced: React.FC = () => {
  return (
    <NL2SQLProvider>
      <PlaygroundContent />
    </NL2SQLProvider>
  );
};
