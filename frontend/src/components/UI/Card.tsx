// src/components/UI/Card.tsx

import * as React from 'react';

interface CardProps {
          children: React.ReactNode;
          className?: string;
          variant?: 'default' | 'glass' | 'gradient';
        }
        
        export function Card({ children, className = '', variant = 'default' }: CardProps) {
          const variantClasses = {
            default: 'bg-gray-800 border border-gray-700',
            glass: 'glass-effect',
            gradient: 'bg-gradient-to-br from-gray-800/50 to-gray-700/50 border border-gray-600/50'
          };
        
          return (
            <div className={`rounded-xl ${variantClasses[variant]} ${className}`}>
              {children}
            </div>
          );
        }