// src/components/Chat/ChatContainer.tsx

import * as React from 'react';
import { useChat } from '@/context/ChatContext';
import { MessageInput } from './MessageInput';
import { MessageList } from './MessageList';
import { StreamingAgent } from '../ReActStream/StreamingAgent';
import { motion, AnimatePresence } from 'framer-motion';

export function ChatContainer() {
  const { messages, currentMessage, isStreaming, error } = useChat();

  const hasMessages = messages.length > 0 || currentMessage;

  return (
    <div className="max-w-4xl mx-auto">
      {/* Welcome State */}
      <AnimatePresence>
        {!hasMessages && (
          <motion.div
            initial={{ opacity: 1 }}
            exit={{ opacity: 0, y: -20 }}
            className="text-center py-16"
          >
            <motion.div
              initial={{ scale: 0.5, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.2, duration: 0.5 }}
              className="mb-8"
            >
              <div className="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-2xl flex items-center justify-center border border-blue-500/30">
                <span className="text-4xl">🤖</span>
              </div>
              
              <h2 className="text-3xl font-bold text-white mb-4">
                Welcome to the NL-to-SQL Agent
              </h2>
              
              <p className="text-xl text-gray-300 mb-8 max-w-2xl mx-auto">
                Ask questions about your database in natural language and watch 
                the AI agent think through the process step-by-step in real-time.
              </p>
            </motion.div>

            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.4, duration: 0.5 }}
              className="grid md:grid-cols-3 gap-4 max-w-3xl mx-auto mb-12"
            >
              <div className="glass-effect rounded-xl p-6 text-center">
                <div className="w-10 h-10 mx-auto mb-3 bg-blue-500/20 rounded-lg flex items-center justify-center">
                  <span className="text-blue-400">💭</span>
                </div>
                <h3 className="font-semibold text-white mb-2">Watch AI Think</h3>
                <p className="text-sm text-gray-400">
                  See the agent's reasoning process unfold in real-time
                </p>
              </div>

              <div className="glass-effect rounded-xl p-6 text-center">
                <div className="w-10 h-10 mx-auto mb-3 bg-green-500/20 rounded-lg flex items-center justify-center">
                  <span className="text-green-400">🔧</span>
                </div>
                <h3 className="font-semibold text-white mb-2">Step-by-Step</h3>
                <p className="text-sm text-gray-400">
                  Follow each action from database exploration to final query
                </p>
              </div>

              <div className="glass-effect rounded-xl p-6 text-center">
                <div className="w-10 h-10 mx-auto mb-3 bg-purple-500/20 rounded-lg flex items-center justify-center">
                  <span className="text-purple-400">✨</span>
                </div>
                <h3 className="font-semibold text-white mb-2">Natural Language</h3>
                <p className="text-sm text-gray-400">
                  No SQL knowledge required - just ask in plain English
                </p>
              </div>
            </motion.div>

            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.6, duration: 0.5 }}
              className="bg-gradient-to-r from-slate-800/50 to-slate-700/50 border border-slate-600/50 rounded-xl p-6 max-w-2xl mx-auto"
            >
              <h4 className="font-semibold text-white mb-4">Try asking:</h4>
              <div className="grid gap-2 text-left">
                <div className="text-gray-300 hover:text-white transition-colors cursor-pointer">
                  • "Who are the top 3 customers by total spending?"
                </div>
                <div className="text-gray-300 hover:text-white transition-colors cursor-pointer">
                  • "Which artists have sold the most albums?"
                </div>
                <div className="text-gray-300 hover:text-white transition-colors cursor-pointer">
                  • "Show me sales by country"
                </div>
                <div className="text-gray-300 hover:text-white transition-colors cursor-pointer">
                  • "What genres are most popular?"
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Chat Messages */}
      <AnimatePresence>
        {hasMessages && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8"
          >
            <MessageList messages={messages} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Current Streaming Message */}
      <AnimatePresence>
        {currentMessage && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="mb-8"
          >
            <StreamingAgent message={currentMessage} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error Display */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="mb-6 p-4 bg-red-900/20 border border-red-500/30 rounded-xl text-red-300"
          >
            <div className="flex items-center gap-2">
              <span className="text-red-400">⚠️</span>
              <span>{error}</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Message Input - Always at bottom */}
      <div className="sticky bottom-4">
        <MessageInput />
      </div>
    </div>
  );
}