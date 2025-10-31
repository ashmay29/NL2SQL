import React, { useState } from 'react';
import { Card } from './ui/Card';
import { Button } from './ui/Button';

interface ClarificationQuestion {
  question: string;
  options?: string[];
  field?: string;
}

interface ClarificationPanelProps {
  questions: string[] | ClarificationQuestion[];
  onAnswer: (answers: Record<string, string>) => void;
  onSkip?: () => void;
  isLoading?: boolean;
}

export const ClarificationPanel: React.FC<ClarificationPanelProps> = ({
  questions,
  onAnswer,
  onSkip,
  isLoading = false,
}) => {
  const [answers, setAnswers] = useState<Record<string, string>>({});

  // Parse questions - handle both string array and object array
  const parsedQuestions: ClarificationQuestion[] = questions.map((q, index) => {
    if (typeof q === 'string') {
      // Try to extract options from string format
      const match = q.match(/^(.*?)\s+Options:\s+(.+)$/);
      if (match) {
        return {
          question: match[1].replace(/^\d+\.\s*/, ''), // Remove numbering
          options: match[2].split(',').map(opt => opt.trim()),
          field: `question_${index}`,
        };
      }
      return {
        question: q.replace(/^\d+\.\s*/, ''), // Remove numbering
        field: `question_${index}`,
      };
    }
    return {
      ...q,
      field: q.field || `question_${index}`,
    };
  });

  const handleOptionSelect = (questionField: string, option: string) => {
    setAnswers(prev => ({
      ...prev,
      [questionField]: option,
    }));
  };

  const handleTextAnswer = (questionField: string, text: string) => {
    setAnswers(prev => ({
      ...prev,
      [questionField]: text,
    }));
  };

  const handleSubmit = () => {
    onAnswer(answers);
  };

  const canSubmit = parsedQuestions.every(q => 
    answers[q.field] && answers[q.field].trim().length > 0
  );

  if (parsedQuestions.length === 0) {
    return null;
  }

  return (
    <Card className="p-6 border-l-4 border-l-blue-500 bg-blue-50">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-lg font-semibold text-blue-900">
              🤔 Need Clarification
            </h3>
            <p className="text-sm text-blue-700 mt-1">
              Your query is ambiguous. Please help us understand what you're looking for.
            </p>
          </div>
          {onSkip && (
            <Button
              variant="outline"
              size="sm"
              onClick={onSkip}
              disabled={isLoading}
            >
              Skip
            </Button>
          )}
        </div>

        {/* Questions */}
        <div className="space-y-4">
          {parsedQuestions.map((question, index) => (
            <div key={question.field} className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">
                {index + 1}. {question.question}
              </label>
              
              {question.options ? (
                // Multiple choice
                <div className="space-y-2">
                  {question.options.map((option) => (
                    <label
                      key={option}
                      className="flex items-center space-x-2 cursor-pointer"
                    >
                      <input
                        type="radio"
                        name={question.field}
                        value={option}
                        checked={answers[question.field] === option}
                        onChange={() => handleOptionSelect(question.field, option)}
                        className="text-blue-600 focus:ring-blue-500"
                        disabled={isLoading}
                      />
                      <span className="text-sm text-gray-700">{option}</span>
                    </label>
                  ))}
                </div>
              ) : (
                // Free text
                <input
                  type="text"
                  value={answers[question.field] || ''}
                  onChange={(e) => handleTextAnswer(question.field, e.target.value)}
                  placeholder="Please specify..."
                  disabled={isLoading}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              )}
            </div>
          ))}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between pt-4 border-t">
          <div className="text-xs text-gray-600">
            {parsedQuestions.length} question{parsedQuestions.length !== 1 ? 's' : ''} • 
            {Object.keys(answers).length} answered
          </div>
          
          <Button
            onClick={handleSubmit}
            disabled={!canSubmit || isLoading}
          >
            {isLoading ? 'Processing...' : 'Submit Answers'}
          </Button>
        </div>
      </div>
    </Card>
  );
};
