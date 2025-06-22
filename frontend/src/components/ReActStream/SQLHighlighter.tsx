// src/components/ReActStream/SQLHighlighter.tsx

import * as React from 'react';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check } from 'lucide-react';
import { SQLHighlighterProps } from '@/services/types';

// Custom SQL theme based on oneDark
const sqlTheme = {
  ...oneDark,
  'pre[class*="language-"]': {
    ...oneDark['pre[class*="language-"]'],
    background: 'rgba(15, 23, 42, 0.8)',
    border: '1px solid rgba(71, 85, 105, 0.3)',
    borderRadius: '8px',
    padding: '16px',
    margin: 0,
    overflow: 'auto',
  },
  'code[class*="language-"]': {
    ...oneDark['code[class*="language-"]'],
    background: 'transparent',
  },
};

export function SQLHighlighter({ sql, animated = false }: SQLHighlighterProps) {
  const [copied, setCopied] = useState(false);
  const [displayedSQL, setDisplayedSQL] = useState('');
  const [isTyping, setIsTyping] = useState(animated);

  // Typewriter effect
  useEffect(() => {
    if (!animated) {
      setDisplayedSQL(sql);
      return;
    }

    setIsTyping(true);
    setDisplayedSQL('');
    
    let currentIndex = 0;
    const interval = setInterval(() => {
      if (currentIndex <= sql.length) {
        setDisplayedSQL(sql.slice(0, currentIndex));
        currentIndex++;
      } else {
        setIsTyping(false);
        clearInterval(interval);
      }
    }, 30); // Adjust speed here

    return () => clearInterval(interval);
  }, [sql, animated]);

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy SQL to clipboard:', err);
    }
  };

  const formatSQL = (sqlString: string) => {
    // Basic SQL formatting - add line breaks for better readability
    return sqlString
      .replace(/\b(SELECT|FROM|WHERE|JOIN|INNER JOIN|LEFT JOIN|RIGHT JOIN|ORDER BY|GROUP BY|HAVING|LIMIT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\b/gi, '\n$1')
      .replace(/,/g, ',\n  ')
      .replace(/\n\s*\n/g, '\n')
      .trim();
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.2 }}
      className="relative group"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-red-500 rounded-full"></div>
          <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
          <div className="w-3 h-3 bg-green-500 rounded-full"></div>
          <span className="ml-2 text-xs text-gray-400 font-mono">SQL Query</span>
        </div>

        {/* Copy Button */}
        <button
          onClick={copyToClipboard}
          className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 p-1 hover:bg-white/10 rounded text-gray-400 hover:text-white"
          title="Copy SQL"
        >
          {copied ? (
            <Check className="w-4 h-4 text-green-400" />
          ) : (
            <Copy className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* SQL Content */}
      <div className="relative">
        <SyntaxHighlighter
          language="sql"
          style={sqlTheme}
          customStyle={{
            fontSize: '14px',
            lineHeight: '1.5',
            fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
          }}
          showLineNumbers={false}
          wrapLines={true}
          wrapLongLines={true}
        >
          {formatSQL(displayedSQL)}
        </SyntaxHighlighter>

        {/* Typing cursor */}
        {isTyping && (
          <motion.div
            className="absolute top-4 bg-blue-400 w-0.5 h-5"
            style={{
              left: `${Math.min(displayedSQL.length * 8 + 16, 300)}px`, // Approximate character width
            }}
            animate={{ opacity: [1, 0] }}
            transition={{ duration: 0.8, repeat: Infinity }}
          />
        )}

        {/* Success notification */}
        {copied && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="absolute top-2 right-2 bg-green-900/80 text-green-300 px-2 py-1 rounded text-xs"
          >
            Copied!
          </motion.div>
        )}
      </div>

      {/* SQL Analysis */}
      <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
        <span>Lines: {displayedSQL.split('\n').length}</span>
        <span>Characters: {displayedSQL.length}</span>
        {displayedSQL.toLowerCase().includes('join') && (
          <span className="text-blue-400">• Contains JOIN</span>
        )}
        {displayedSQL.toLowerCase().includes('group by') && (
          <span className="text-green-400">• Uses aggregation</span>
        )}
        {displayedSQL.toLowerCase().includes('order by') && (
          <span className="text-purple-400">• Has sorting</span>
        )}
      </div>
    </motion.div>
  );
}