import { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
}

export const Card = ({ children, className = '', hover = false }: CardProps) => {
  return (
    <div
      className={`
        bg-white rounded-xl border border-apple-gray-200 p-6 transition-all
        ${hover ? 'hover:border-apple-gray-300 hover:shadow-sm' : ''}
        ${className}
      `}
    >
      {children}
    </div>
  );
};
