// src/components/Chat/MessageInput.tsx

import * as React from 'react';
import { useState, useRef, useEffect } from 'react';
import { Send, Square, Loader2 } from 'lucide-react';
import { useChat } from '@/context/ChatContext';
import { motion } from 'framer-motion';

export function MessageInput() {
  const [question, setQuestion] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { sendMessage, stopStreaming, isStreaming } = useChat();

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }
  }, [question]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || isStreaming) return;

    sendMessage(question.trim());
    setQuestion('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && !isStreaming) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleStop = () => {
    stopStreaming();
  };

  const exampleQuestions = [
    "Who are the top 3 customers by total spending?",
    "Which artists have sold the most albums?",
    "Show me sales by country",
    "What genres are most popular?"
  ];

  const handleExampleClick = (example: string) => {
    if (isStreaming) return;
    setQuestion(example);
    textareaRef.current?.focus();
  };

  return (
    <div className="space-y-4">
      {/* Example Questions - Only show when not streaming and no current input */}
      {!isStreaming && !question.trim() && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-wrap gap-2 justify-center"
        >
          {exampleQuestions.map((example, index) => (
            <motion.button
              key={index}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: index * 0.1 }}
              onClick={() => handleExampleClick(example)}
              className="px-3 py-2 text-sm bg-dark-700/50 hover:bg-dark-600/50 border border-slate-600/50 hover:border-slate-500/50 rounded-lg text-gray-300 hover:text-white transition-all duration-200"
            >
              {example}
            </motion.button>
          ))}
        </motion.div>
      )}

      {/* Input Form */}
      <motion.form
        onSubmit={handleSubmit}
        className={`glass-effect rounded-2xl transition-all duration-300 ${
          isFocused ? 'ring-2 ring-blue-500/50' : ''
        }`}
        layout
      >
        <div className="flex items-end gap-3 p-4">
          <div className="flex-1">
            <textarea
              ref={textareaRef}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              placeholder="Ask a question about your database..."
              disabled={isStreaming}
              className="w-full bg-transparent text-white placeholder-gray-400 border-none outline-none resize-none min-h-[24px] max-h-[120px] disabled:opacity-50"
              rows={1}
            />
          </div>

          {/* Action Button */}
          {isStreaming ? (
            <motion.button
              type="button"
              onClick={handleStop}
              className="p-3 bg-red-600/20 hover:bg-red-600/30 border border-red-500/30 hover:border-red-500/50 rounded-xl text-red-400 hover:text-red-300 transition-all duration-200 flex items-center justify-center"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Square className="w-5 h-5" />
            </motion.button>
          ) : (
            <motion.button
              type="submit"
              disabled={!question.trim()}
              className={`p-3 rounded-xl transition-all duration-200 flex items-center justify-center ${
                question.trim()
                  ? 'bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/30 hover:border-blue-500/50 text-blue-400 hover:text-blue-300'
                  : 'bg-gray-600/20 border border-gray-500/30 text-gray-500 cursor-not-allowed'
              }`}
              whileHover={question.trim() ? { scale: 1.05 } : {}}
              whileTap={question.trim() ? { scale: 0.95 } : {}}
            >
              <Send className="w-5 h-5" />
            </motion.button>
          )}
        </div>

        {/* Streaming Indicator */}
        {isStreaming && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="px-4 pb-3"
          >
            <div className="flex items-center gap-2 text-sm text-blue-400">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>AI is thinking and processing your request...</span>
            </div>
          </motion.div>
        )}

        {/* Hint Text */}
        {!isStreaming && isFocused && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="px-4 pb-3 text-xs text-gray-500"
          >
            Press Enter to send, Shift+Enter for new line
          </motion.div>
        )}
      </motion.form>
    </div>
  );
}