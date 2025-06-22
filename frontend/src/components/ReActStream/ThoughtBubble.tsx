// src/components/ReActStream/ThoughtBubble.tsx

import * as React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain } from 'lucide-react';
import { ThoughtBubbleProps } from '@/services/types';

export function ThoughtBubble({ thought, stepNumber, isVisible }: ThoughtBubbleProps) {
  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, scale: 0.8, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.8, y: -10 }}
          transition={{ type: 'spring', damping: 20, stiffness: 300 }}
          className="mb-4"
        >
          <div className="thought-bubble relative">
            {/* Step indicator */}
            <div className="flex items-center gap-2 mb-2">
              <div className="w-6 h-6 bg-blue-500/20 rounded-full flex items-center justify-center">
                <span className="text-xs font-bold text-blue-400">{stepNumber}</span>
              </div>
              <div className="flex items-center gap-1 text-xs text-blue-300">
                <Brain className="w-3 h-3" />
                <span>Thinking</span>
              </div>
            </div>

            {/* Thought content */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="relative"
            >
              <div className="bg-gradient-to-br from-blue-600/20 to-purple-600/20 border border-blue-500/30 rounded-2xl p-4 relative">
                <p className="text-blue-100 text-sm leading-relaxed">
                  {thought}
                </p>

                {/* Floating particles for thinking effect */}
                <div className="absolute inset-0 pointer-events-none">
                  {[...Array(3)].map((_, i) => (
                    <motion.div
                      key={i}
                      className="absolute w-1 h-1 bg-blue-400 rounded-full opacity-60"
                      style={{
                        left: `${20 + i * 30}%`,
                        top: `${10 + i * 5}%`,
                      }}
                      animate={{
                        y: [-5, -15, -5],
                        opacity: [0.3, 0.8, 0.3],
                      }}
                      transition={{
                        duration: 2,
                        repeat: Infinity,
                        delay: i * 0.3,
                      }}
                    />
                  ))}
                </div>
              </div>

              {/* Speech bubble tail */}
              <div className="absolute -bottom-2 left-6 w-4 h-4 bg-gradient-to-br from-blue-600/20 to-purple-600/20 border-b border-r border-blue-500/30 rotate-45" />
            </motion.div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}