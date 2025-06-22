// src/components/ReActStream/StreamingAgent.tsx

import * as React from 'react';
import { useEffect, useRef } from 'react';
import { ChatMessage } from '@/services/types';
import { motion, AnimatePresence } from 'framer-motion';
import { User, Bot, Clock, Loader2 } from 'lucide-react';
import { ThoughtBubble } from '../ReActStream/ThoughtBubble';
import { ActionCard } from '../ReActStream/ActionCard';
import { ProgressIndicator } from '../ReActStream/ProgressIndicator';
import { FinalAnswer } from '../ReActStream/FinalAnswer';

interface StreamingAgentProps {
  message: ChatMessage;
}

export function StreamingAgent({ message }: StreamingAgentProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new steps are added
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [message.steps.length]);

  const currentStep = message.steps[message.steps.length - 1];
  const isThinking = message.status === 'thinking';
  const isProcessing = message.status === 'processing';
  const isCompleted = message.status === 'completed';
  const hasError = message.status === 'error';

  return (
    <div className="space-y-6">
      {/* User Question */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-start gap-3"
      >
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
      </motion.div>

      {/* AI Response Container */}
      <div className="flex items-start gap-3">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.2, type: 'spring' }}
          className="w-8 h-8 rounded-full bg-purple-500/20 flex items-center justify-center flex-shrink-0 sticky top-20"
        >
          <Bot className="w-4 h-4 text-purple-400" />
        </motion.div>

        <div className="flex-1 space-y-4">
          {/* Status Header */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
            className="flex items-center gap-3"
          >
            <div className="flex items-center gap-2">
              {isThinking && (
                <>
                  <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                  <span className="text-sm text-blue-400">AI is thinking...</span>
                </>
              )}
              {isProcessing && (
                <>
                  <Clock className="w-4 h-4 text-yellow-400" />
                  <span className="text-sm text-yellow-400">Processing step {message.steps.length}...</span>
                </>
              )}
              {isCompleted && (
                <>
                  <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse-glow"></div>
                  <span className="text-sm text-green-400">Completed successfully!</span>
                </>
              )}
              {hasError && (
                <>
                  <div className="w-2 h-2 bg-red-400 rounded-full"></div>
                  <span className="text-sm text-red-400">Error occurred</span>
                </>
              )}
            </div>

            {/* Progress Indicator */}
            {!isThinking && (
              <ProgressIndicator
                currentStep={message.steps.length}
                isComplete={isCompleted}
              />
            )}
          </motion.div>

          {/* Thinking State */}
          <AnimatePresence>
            {isThinking && (
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                className="thought-bubble"
              >
                <div className="flex items-center gap-3">
                  <div className="flex gap-1">
                    <motion.div
                      className="w-2 h-2 bg-blue-400 rounded-full"
                      animate={{ scale: [1, 1.2, 1] }}
                      transition={{ duration: 1, repeat: Infinity, delay: 0 }}
                    />
                    <motion.div
                      className="w-2 h-2 bg-blue-400 rounded-full"
                      animate={{ scale: [1, 1.2, 1] }}
                      transition={{ duration: 1, repeat: Infinity, delay: 0.2 }}
                    />
                    <motion.div
                      className="w-2 h-2 bg-blue-400 rounded-full"
                      animate={{ scale: [1, 1.2, 1] }}
                      transition={{ duration: 1, repeat: Infinity, delay: 0.4 }}
                    />
                  </div>
                  <span className="text-blue-300">
                    Analyzing your question and planning approach...
                  </span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* ReAct Steps */}
          <AnimatePresence>
            {message.steps.map((step, index) => (
              <motion.div
                key={step.step_number}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                {/* Thought Bubble */}
                {step.thought && (
                  <ThoughtBubble
                    thought={step.thought}
                    stepNumber={step.step_number}
                    isVisible={true}
                  />
                )}

                {/* Action Card */}
                <ActionCard
                  action={step.action}
                  stepNumber={step.step_number}
                  thought={step.thought}
                  isCompleted={!!step.observation}
                  observation={step.observation}
                />
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Error Message */}
          <AnimatePresence>
            {hasError && message.error_message && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="bg-red-900/20 border border-red-500/30 rounded-xl p-4"
              >
                <div className="flex items-center gap-2 text-red-300">
                  <span className="text-red-400">⚠️</span>
                  <span>{message.error_message}</span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Final Answer */}
          <AnimatePresence>
            {isCompleted && message.answer && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2, type: 'spring' }}
              >
                <FinalAnswer
                  answer={message.answer}
                  totalSteps={message.steps.length}
                  executionTime={message.execution_time}
                  onNewQuestion={() => {
                    // Scroll to input
                    const input = document.querySelector('textarea');
                    input?.focus();
                  }}
                />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Auto-scroll anchor */}
          <div ref={bottomRef} />
        </div>
      </div>
    </div>
  );
}