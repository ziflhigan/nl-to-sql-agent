// src/components/Chat/MessageList.tsx

import * as React from 'react';
import { useState } from 'react';
import { ChatMessage } from '@/services/types';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, Clock, CheckCircle, XCircle, User, Bot } from 'lucide-react';
import { ActionCard } from '../ReActStream/ActionCard';
import { FinalAnswer } from '../ReActStream/FinalAnswer';

interface MessageListProps {
  messages: ChatMessage[];
}

interface MessageItemProps {
  message: ChatMessage;
  index: number;
}

function MessageItem({ message, index }: MessageItemProps) {
  const [showDetails, setShowDetails] = useState(false);

  const getStatusIcon = () => {
    switch (message.status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'error':
        return <XCircle className="w-4 h-4 text-red-400" />;
      default:
        return <Clock className="w-4 h-4 text-yellow-400" />;
    }
  };

  const getStatusColor = () => {
    switch (message.status) {
      case 'completed':
        return 'border-green-500/30 bg-green-900/10';
      case 'error':
        return 'border-red-500/30 bg-red-900/10';
      default:
        return 'border-yellow-500/30 bg-yellow-900/10';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="space-y-4"
    >
      {/* User Question */}
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0">
          <User className="w-4 h-4 text-blue-400" />
        </div>
        <div className="flex-1">
          <div className="bg-blue-500/10 border border-blue-500/20 rounded-2xl rounded-tl-md p-4">
            <p className="text-white">{message.question}</p>
          </div>
          <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
            <span>{new Date(message.timestamp).toLocaleTimeString()}</span>
          </div>
        </div>
      </div>

      {/* AI Response */}
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-full bg-purple-500/20 flex items-center justify-center flex-shrink-0">
          <Bot className="w-4 h-4 text-purple-400" />
        </div>
        <div className="flex-1">
          <div className={`border rounded-2xl rounded-tl-md p-4 ${getStatusColor()}`}>
            {/* Status Header */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                {getStatusIcon()}
                <span className="text-sm font-medium text-white">
                  {message.status === 'completed' ? 'Completed' : 
                   message.status === 'error' ? 'Error' : 'Processing'}
                </span>
                {message.execution_time && (
                  <span className="text-xs text-gray-400">
                    • {message.execution_time}s
                  </span>
                )}
              </div>

              {/* Toggle Details Button */}
              {message.steps.length > 0 && (
                <button
                  onClick={() => setShowDetails(!showDetails)}
                  className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors duration-200"
                >
                  <span>{showDetails ? 'Hide' : 'Show'} process</span>
                  {showDetails ? 
                    <ChevronUp className="w-3 h-3" /> : 
                    <ChevronDown className="w-3 h-3" />
                  }
                </button>
              )}
            </div>

            {/* Final Answer */}
            {message.answer && (
              <FinalAnswer
                answer={message.answer}
                totalSteps={message.steps.length}
                executionTime={message.execution_time}
                onNewQuestion={() => {}}
                isCompact={true}
              />
            )}

            {/* Error Message */}
            {message.status === 'error' && message.error_message && (
              <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-3 text-red-300">
                <p className="text-sm">{message.error_message}</p>
              </div>
            )}

            {/* Expandable Details */}
            <AnimatePresence>
              {showDetails && message.steps.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mt-4 pt-4 border-t border-gray-600/30"
                >
                  <h4 className="text-sm font-medium text-gray-300 mb-3">
                    AI Reasoning Process ({message.steps.length} steps)
                  </h4>
                  
                  <div className="space-y-3">
                    {message.steps.map((step, stepIndex) => (
                      <motion.div
                        key={step.step_number}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: stepIndex * 0.05 }}
                      >
                        <ActionCard
                          action={step.action}
                          stepNumber={step.step_number}
                          thought={step.thought}
                          isCompleted={!!step.observation}
                          observation={step.observation}
                          isCompact={true}
                        />
                      </motion.div>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
            <span>{new Date(message.timestamp).toLocaleTimeString()}</span>
            {message.steps.length > 0 && (
              <span>• {message.steps.length} steps</span>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

export function MessageList({ messages }: MessageListProps) {
  if (messages.length === 0) {
    return null;
  }

  return (
    <div className="space-y-8">
      {messages.map((message, index) => (
        <MessageItem key={message.id} message={message} index={index} />
      ))}
    </div>
  );
}