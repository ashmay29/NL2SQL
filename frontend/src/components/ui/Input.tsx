import { InputHTMLAttributes } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = ({ label, error, className = '', ...props }: InputProps) => {
  return (
    <div className="w-full">
      {label && (
        <label className="block text-sm font-medium text-apple-gray-700 mb-2">
          {label}
        </label>
      )}
      <input
        className={`
          w-full px-4 py-2.5 rounded-xl border border-apple-gray-200
          bg-white text-apple-gray-900 placeholder-apple-gray-400
          focus:outline-none focus:ring-2 focus:ring-apple-blue focus:border-transparent
          transition-all duration-200
          ${error ? 'border-apple-red focus:ring-apple-red' : ''}
          ${className}
        `}
        {...props}
      />
      {error && (
        <p className="mt-1.5 text-sm text-apple-red">{error}</p>
      )}
    </div>
  );
};
