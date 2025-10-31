import React, { useState } from 'react';
import { Card } from './ui/Card';
import { Button } from './ui/Button';

interface FeedbackFormProps {
  originalQuery: string;
  generatedSQL: string;
  onSubmit: (feedback: {
    correctedSQL: string;
    reason: string;
    rating: number;
  }) => void;
  onCancel?: () => void;
  isSubmitting?: boolean;
}

export const FeedbackForm: React.FC<FeedbackFormProps> = ({
  originalQuery,
  generatedSQL,
  onSubmit,
  onCancel,
  isSubmitting = false,
}) => {
  const [correctedSQL, setCorrectedSQL] = useState(generatedSQL);
  const [reason, setReason] = useState('');
  const [rating, setRating] = useState<number>(3);
  const [feedbackType, setFeedbackType] = useState<'correction' | 'confirmation'>('correction');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    onSubmit({
      correctedSQL: feedbackType === 'correction' ? correctedSQL : generatedSQL,
      reason: reason.trim(),
      rating,
    });
  };

  const isValid = () => {
    if (feedbackType === 'correction') {
      return correctedSQL.trim() !== '' && correctedSQL !== generatedSQL && reason.trim() !== '';
    }
    return true; // Confirmation doesn't require changes
  };

  return (
    <Card className="p-6 border-l-4 border-l-green-500 bg-green-50">
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Header */}
        <div>
          <h3 className="text-lg font-semibold text-green-900">
            💬 Provide Feedback
          </h3>
          <p className="text-sm text-green-700 mt-1">
            Help improve the system by confirming correct results or providing corrections.
          </p>
        </div>

        {/* Original Query Display */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">
            Original Query
          </label>
          <div className="bg-gray-100 p-3 rounded border text-sm">
            {originalQuery}
          </div>
        </div>

        {/* Feedback Type */}
        <div className="space-y-3">
          <label className="block text-sm font-medium text-gray-700">
            Feedback Type
          </label>
          <div className="flex space-x-4">
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="radio"
                name="feedbackType"
                value="confirmation"
                checked={feedbackType === 'confirmation'}
                onChange={(e) => setFeedbackType(e.target.value as 'confirmation')}
                className="text-green-600 focus:ring-green-500"
                disabled={isSubmitting}
              />
              <span className="text-sm">✅ SQL is correct</span>
            </label>
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="radio"
                name="feedbackType"
                value="correction"
                checked={feedbackType === 'correction'}
                onChange={(e) => setFeedbackType(e.target.value as 'correction')}
                className="text-green-600 focus:ring-green-500"
                disabled={isSubmitting}
              />
              <span className="text-sm">✏️ SQL needs correction</span>
            </label>
          </div>
        </div>

        {/* Rating */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">
            Overall Rating
          </label>
          <div className="flex items-center space-x-2">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                type="button"
                onClick={() => setRating(star)}
                disabled={isSubmitting}
                className={`text-2xl transition-colors ${
                  star <= rating ? 'text-yellow-400' : 'text-gray-300'
                } hover:text-yellow-400`}
              >
                ⭐
              </button>
            ))}
            <span className="text-sm text-gray-600 ml-2">
              {rating}/5 stars
            </span>
          </div>
        </div>

        {/* SQL Editor (only for corrections) */}
        {feedbackType === 'correction' && (
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              Corrected SQL
            </label>
            <textarea
              value={correctedSQL}
              onChange={(e) => setCorrectedSQL(e.target.value)}
              rows={6}
              disabled={isSubmitting}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent font-mono text-sm"
              placeholder="Enter the corrected SQL..."
            />
          </div>
        )}

        {/* Reason/Comments */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">
            {feedbackType === 'correction' ? 'What was wrong?' : 'Comments (optional)'}
          </label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            disabled={isSubmitting}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
            placeholder={
              feedbackType === 'correction'
                ? "Explain what was incorrect and why your version is better..."
                : "Any additional comments about the query or results..."
            }
          />
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between pt-4 border-t">
          <div className="text-xs text-gray-600">
            Your feedback helps improve the system for everyone
          </div>
          
          <div className="flex space-x-3">
            {onCancel && (
              <Button
                type="button"
                variant="outline"
                onClick={onCancel}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
            )}
            
            <Button
              type="submit"
              disabled={!isValid() || isSubmitting}
            >
              {isSubmitting ? 'Submitting...' : 'Submit Feedback'}
            </Button>
          </div>
        </div>
      </form>
    </Card>
  );
};
