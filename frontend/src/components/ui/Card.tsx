import { motion } from 'framer-motion';
import { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
}

export const Card = ({ children, className = '', hover = false }: CardProps) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      whileHover={hover ? { y: -2, boxShadow: '0 12px 32px rgba(0, 0, 0, 0.1)' } : {}}
      className={`bg-white rounded-2xl shadow-apple p-6 ${className}`}
    >
      {children}
    </motion.div>
  );
};
