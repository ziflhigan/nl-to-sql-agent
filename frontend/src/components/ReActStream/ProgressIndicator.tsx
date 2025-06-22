// src/components/ReActStream/ProgressIndicator.tsx

import * as React from 'react';
import { motion } from 'framer-motion';
import { CheckCircle, Circle, Clock } from 'lucide-react';
import { ProgressIndicatorProps } from '@/services/types';

export function ProgressIndicator({ currentStep, totalSteps, isComplete }: ProgressIndicatorProps) {
  // Estimate total steps if not provided (common patterns in ReAct)
  const estimatedTotal = totalSteps || Math.max(currentStep + 1, 3);
  const progress = isComplete ? 100 : Math.min((currentStep / estimatedTotal) * 100, 90);

  return (
    <div className="flex items-center gap-3">
      {/* Progress Bar */}
      <div className="flex-1 max-w-32">
        <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          />
        </div>
      </div>

      {/* Step Counter */}
      <div className="flex items-center gap-2 text-xs">
        {isComplete ? (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', delay: 0.2 }}
            className="flex items-center gap-1 text-green-400"
          >
            <CheckCircle className="w-3 h-3" />
            <span>Complete</span>
          </motion.div>
        ) : (
          <div className="flex items-center gap-1 text-blue-400">
            <Clock className="w-3 h-3 animate-pulse" />
            <span>Step {currentStep}</span>
            {totalSteps && <span>of {totalSteps}</span>}
          </div>
        )}
      </div>

      {/* Mini Step Indicators */}
      <div className="hidden sm:flex items-center gap-1">
        {Array.from({ length: Math.min(estimatedTotal, 5) }, (_, index) => {
          const stepNumber = index + 1;
          const isActive = stepNumber <= currentStep;
          const isCurrent = stepNumber === currentStep && !isComplete;
          
          return (
            <motion.div
              key={stepNumber}
              initial={{ scale: 0.8, opacity: 0.5 }}
              animate={{ 
                scale: isCurrent ? 1.2 : 1,
                opacity: isActive ? 1 : 0.3 
              }}
              transition={{ duration: 0.2 }}
              className="relative"
            >
              {isActive ? (
                <CheckCircle className="w-3 h-3 text-blue-400" />
              ) : (
                <Circle className="w-3 h-3 text-gray-500" />
              )}
              
              {isCurrent && (
                <motion.div
                  className="absolute inset-0 rounded-full border-2 border-blue-400"
                  animate={{ scale: [1, 1.5, 1], opacity: [1, 0, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
              )}
            </motion.div>
          );
        })}
        
        {estimatedTotal > 5 && (
          <span className="text-xs text-gray-500 ml-1">...</span>
        )}
      </div>
    </div>
  );
}