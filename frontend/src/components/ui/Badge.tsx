import { ReactNode } from 'react';

interface BadgeProps {
  children: ReactNode;
  variant?: 'success' | 'warning' | 'error' | 'info' | 'neutral';
  className?: string;
}

export const Badge = ({ children, variant = 'neutral', className = '' }: BadgeProps) => {
  const variantClasses = {
    success: 'bg-apple-green/10 text-apple-green border-apple-green/20',
    warning: 'bg-apple-orange/10 text-apple-orange border-apple-orange/20',
    error: 'bg-apple-red/10 text-apple-red border-apple-red/20',
    info: 'bg-apple-blue/10 text-apple-blue border-apple-blue/20',
    neutral: 'bg-apple-gray-100 text-apple-gray-700 border-apple-gray-200',
  };

  return (
    <span
      className={`
        inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium border
        ${variantClasses[variant]}
        ${className}
      `}
    >
      {children}
    </span>
  );
};
