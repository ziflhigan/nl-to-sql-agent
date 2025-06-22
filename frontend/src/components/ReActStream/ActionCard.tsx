// src/components/ReActStream/ActionCard.tsx

import * as React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Database, 
  Search, 
  CheckCircle, 
  Loader2, 
  Eye,
  Code,
  FileText,
  Shield
} from 'lucide-react';
import { ActionCardProps } from '@/services/types';
import { SQLHighlighter } from './SQLHighlighter';
import { ObservationPanel } from './ObservationPanel';

const getCategoryIcon = (category: string) => {
  switch (category) {
    case 'schema_exploration':
      return Database;
    case 'data_retrieval':
      return Search;
    case 'validation':
      return Shield;
    default:
      return Code;
  }
};

const getCategoryColor = (category: string) => {
  switch (category) {
    case 'schema_exploration':
      return 'from-blue-600/20 to-blue-500/10 border-blue-500/30';
    case 'data_retrieval':
      return 'from-green-600/20 to-green-500/10 border-green-500/30';
    case 'validation':
      return 'from-orange-600/20 to-orange-500/10 border-orange-500/30';
    default:
      return 'from-gray-600/20 to-gray-500/10 border-gray-500/30';
  }
};

const getCategoryBadgeColor = (category: string) => {
  switch (category) {
    case 'schema_exploration':
      return 'bg-blue-500/20 text-blue-300 border-blue-500/30';
    case 'data_retrieval':
      return 'bg-green-500/20 text-green-300 border-green-500/30';
    case 'validation':
      return 'bg-orange-500/20 text-orange-300 border-orange-500/30';
    default:
      return 'bg-gray-500/20 text-gray-300 border-gray-500/30';
  }
};

interface ExtendedActionCardProps extends ActionCardProps {
  observation?: any;
  isCompact?: boolean;
}

export function ActionCard({ 
  action, 
  stepNumber, 
  thought, 
  isCompleted, 
  observation,
  isCompact = false 
}: ExtendedActionCardProps) {
  const IconComponent = getCategoryIcon(action.category);
  const cardColors = getCategoryColor(action.category);
  const badgeColors = getCategoryBadgeColor(action.category);

  const isSQL = action.tool.includes('query') && typeof action.input === 'string' && action.input.trim();
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: 'spring', damping: 20, stiffness: 300 }}
      className={`action-card bg-gradient-to-r ${cardColors} ${isCompact ? 'p-4' : 'p-6'} mb-4`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-white/10 rounded-lg flex items-center justify-center">
              <IconComponent className="w-4 h-4 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-white">Step {stepNumber}</span>
                <span className={`px-2 py-1 rounded-lg text-xs font-medium border ${badgeColors}`}>
                  {action.category.replace('_', ' ')}
                </span>
              </div>
              <p className="text-sm text-gray-300 mt-1">{action.description}</p>
            </div>
          </div>
        </div>

        {/* Status Indicator */}
        <div className="flex items-center gap-2">
          {isCompleted ? (
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', delay: 0.2 }}
            >
              <CheckCircle className="w-5 h-5 text-green-400" />
            </motion.div>
          ) : (
            <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
          )}
        </div>
      </div>

      {/* Purpose */}
      {!isCompact && (
        <div className="mb-4 p-3 bg-white/5 rounded-lg">
          <div className="flex items-center gap-2 mb-1">
            <Eye className="w-3 h-3 text-gray-400" />
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">
              Purpose
            </span>
          </div>
          <p className="text-sm text-gray-300">{action.purpose}</p>
        </div>
      )}

      {/* Action Input */}
      <AnimatePresence>
        {action.input && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            transition={{ delay: 0.1 }}
            className="mb-4"
          >
            {isSQL ? (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Code className="w-4 h-4 text-purple-400" />
                  <span className="text-sm font-medium text-purple-300">
                    SQL Query
                  </span>
                </div>
                <SQLHighlighter sql={action.input} animated={!isCompleted} />
              </div>
            ) : (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <FileText className="w-4 h-4 text-gray-400" />
                  <span className="text-sm font-medium text-gray-300">
                    Input
                  </span>
                </div>
                <div className="sql-container">
                <pre className="text-sm text-gray-300 whitespace-pre-wrap">
                  {typeof action.input === 'object' 
                    ? JSON.stringify(action.input, null, 2) 
                    : action.input}
                </pre>
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Observation/Result */}
      <AnimatePresence>
        {isCompleted && observation && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <ObservationPanel observation={observation} stepNumber={stepNumber} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Loading State */}
      <AnimatePresence>
        {!isCompleted && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="mt-4 flex items-center gap-2 text-sm text-blue-300"
          >
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Executing action...</span>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}