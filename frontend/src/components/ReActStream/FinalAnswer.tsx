// src/components/ReActStream/FinalAnswer.tsx

import * as React from 'react';
import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  CheckCircle, 
  Clock, 
  Sparkles, 
  MessageCircle, 
  Copy, 
  Check,
  RotateCcw,
  TrendingUp
} from 'lucide-react';
import { FinalAnswerProps } from '@/services/types';

interface ExtendedFinalAnswerProps extends FinalAnswerProps {
  isCompact?: boolean;
}

export function FinalAnswer({ 
  answer, 
  totalSteps, 
  executionTime, 
  onNewQuestion, 
  isCompact = false 
}: ExtendedFinalAnswerProps) {
  const [copied, setCopied] = useState(false);
  const [showCelebration, setShowCelebration] = useState(!isCompact);

  useEffect(() => {
    if (!isCompact) {
      // Show celebration effect
      const timer = setTimeout(() => {
        setShowCelebration(false);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [isCompact]);

  const copyAnswer = async () => {
    try {
      await navigator.clipboard.writeText(answer);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy answer:', err);
    }
  };

  const celebrationVariants = {
    hidden: { opacity: 0, scale: 0 },
    visible: { 
      opacity: 1, 
      scale: 1,
      transition: { 
        type: 'spring',
        damping: 15,
        stiffness: 300 
      }
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', damping: 20, stiffness: 300 }}
      className={`relative ${isCompact ? 'bg-green-900/10 border border-green-500/20' : 'bg-gradient-to-br from-green-900/20 to-emerald-900/20 border border-green-500/30'} rounded-2xl ${isCompact ? 'p-4' : 'p-6'} overflow-hidden`}
    >
      {/* Celebration Effect */}
      <AnimatePresence>
        {showCelebration && !isCompact && (
          <motion.div className="absolute inset-0 pointer-events-none">
            {/* Sparkles */}
            {Array.from({ length: 8 }, (_, i) => (
              <motion.div
                key={i}
                className="absolute"
                style={{
                  left: `${10 + (i * 10)}%`,
                  top: `${10 + (i % 3) * 30}%`,
                }}
                variants={celebrationVariants as any}
                initial="hidden"
                animate="visible"
                exit="hidden"
                transition={{ delay: i * 0.1 }}
              >
                <Sparkles className="w-4 h-4 text-yellow-400" />
              </motion.div>
            ))}
            
            {/* Floating particles */}
            {Array.from({ length: 6 }, (_, i) => (
              <motion.div
                key={`particle-${i}`}
                className="absolute w-2 h-2 bg-gradient-to-r from-green-400 to-blue-400 rounded-full"
                style={{
                  left: `${20 + i * 15}%`,
                  top: '50%',
                }}
                animate={{
                  y: [-10, -30, -10],
                  x: [0, Math.sin(i) * 20, 0],
                  opacity: [0, 1, 0],
                }}
                transition={{
                  duration: 2,
                  delay: i * 0.2,
                  repeat: 1,
                }}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', delay: 0.2 }}
            className="w-10 h-10 bg-green-500/20 rounded-full flex items-center justify-center"
          >
            <CheckCircle className="w-5 h-5 text-green-400" />
          </motion.div>
          
          <div>
            <h3 className={`font-bold text-green-300 ${isCompact ? 'text-lg' : 'text-xl'}`}>
              {isCompact ? 'Answer' : 'Final Answer'}
            </h3>
            {!isCompact && (
              <p className="text-sm text-green-400/80">
                Query completed successfully
              </p>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={copyAnswer}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors duration-200 text-gray-400 hover:text-white"
            title="Copy answer"
          >
            {copied ? (
              <Check className="w-4 h-4 text-green-400" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* Answer Content */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className={`${isCompact ? 'bg-white/5' : 'bg-white/10'} rounded-xl p-4 mb-4`}
      >
        <p className={`text-white leading-relaxed ${isCompact ? 'text-sm' : 'text-base'}`}>
          {answer}
        </p>
      </motion.div>

      {/* Metadata */}
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-4 text-green-400/80">
          <div className="flex items-center gap-1">
            <TrendingUp className="w-3 h-3" />
            <span>{totalSteps} steps</span>
          </div>
          {executionTime && (
            <div className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              <span>{executionTime}s</span>
            </div>
          )}
        </div>

        {!isCompact && (
          <div className="flex items-center gap-2">
            <motion.button
              onClick={onNewQuestion}
              className="flex items-center gap-2 px-3 py-1.5 bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/30 hover:border-blue-500/50 rounded-lg text-blue-300 hover:text-blue-200 transition-all duration-200 text-sm"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <MessageCircle className="w-3 h-3" />
              <span>Ask another question</span>
            </motion.button>
          </div>
        )}
      </div>

      {/* Success notification for copy */}
      <AnimatePresence>
        {copied && (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.9 }}
            className="absolute top-4 right-4 bg-green-900/80 text-green-300 px-3 py-1 rounded-lg text-sm"
          >
            Answer copied!
          </motion.div>
        )}
      </AnimatePresence>

      {/* Shimmer effect */}
      <div className="absolute inset-0 -top-[1px] bg-gradient-to-r from-transparent via-white/5 to-transparent shimmer-effect rounded-2xl" />
    </motion.div>
  );
}