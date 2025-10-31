import React from 'react';
import { Badge } from './ui/Badge';

interface ComplexityBadgeProps {
  level: 'simple' | 'moderate' | 'complex' | 'very_complex';
  score?: number;
  warnings?: string[];
  className?: string;
}

export const ComplexityBadge: React.FC<ComplexityBadgeProps> = ({
  level,
  score,
  warnings = [],
  className = '',
}) => {
  const getVariant = (level: string) => {
    switch (level) {
      case 'simple':
        return 'success';
      case 'moderate':
        return 'secondary';
      case 'complex':
        return 'warning';
      case 'very_complex':
        return 'error';
      default:
        return 'secondary';
    }
  };

  const getIcon = (level: string) => {
    switch (level) {
      case 'simple':
        return '🟢';
      case 'moderate':
        return '🟡';
      case 'complex':
        return '🟠';
      case 'very_complex':
        return '🔴';
      default:
        return '⚪';
    }
  };

  const getDescription = (level: string) => {
    switch (level) {
      case 'simple':
        return 'Fast execution expected';
      case 'moderate':
        return 'Good performance expected';
      case 'complex':
        return 'May require optimization';
      case 'very_complex':
        return 'Consider breaking into smaller queries';
      default:
        return 'Unknown complexity';
    }
  };

  return (
    <div className={`inline-flex items-center space-x-2 ${className}`}>
      <Badge variant={getVariant(level)} className="flex items-center space-x-1">
        <span>{getIcon(level)}</span>
        <span className="capitalize">{level.replace('_', ' ')}</span>
        {score && <span>({score})</span>}
      </Badge>
      
      {warnings.length > 0 && (
        <div className="group relative">
          <span className="text-yellow-500 cursor-help">⚠️</span>
          <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 hidden group-hover:block z-10">
            <div className="bg-black text-white text-xs rounded py-2 px-3 max-w-xs">
              <div className="font-semibold mb-1">Performance Warnings:</div>
              <ul className="space-y-1">
                {warnings.map((warning, index) => (
                  <li key={index} className="text-xs">• {warning}</li>
                ))}
              </ul>
              <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-black"></div>
            </div>
          </div>
        </div>
      )}
      
      <span className="text-xs text-gray-500 hidden sm:inline">
        {getDescription(level)}
      </span>
    </div>
  );
};
