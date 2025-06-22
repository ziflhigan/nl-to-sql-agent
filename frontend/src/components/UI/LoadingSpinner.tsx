// src/components/UI/LoadingSpinner.tsx

import * as React from 'react';
import { Loader2 } from "lucide-react";

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  color?: 'blue' | 'white' | 'gray';
}

export function LoadingSpinner({ size = 'md', color = 'blue' }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8'
  };

  const colorClasses = {
    blue: 'text-blue-400',
    white: 'text-white',
    gray: 'text-gray-400'
  };

  return (
    <Loader2 className={`animate-spin ${sizeClasses[size]} ${colorClasses[color]}`} />
  );
}