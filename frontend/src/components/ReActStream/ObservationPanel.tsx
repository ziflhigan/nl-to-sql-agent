// src/components/ReActStream/ObservationPanel.tsx

import * as React from 'react';
import { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Eye, 
  CheckCircle, 
  AlertCircle, 
  Table, 
  FileText, 
  Database,
  ChevronDown,
  ChevronUp,
  Copy
} from 'lucide-react';
import { ObservationPanelProps } from '@/services/types';

export function ObservationPanel({ observation, stepNumber }: ObservationPanelProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [copied, setCopied] = useState(false);

  const getResultIcon = () => {
    switch (observation.result_type) {
      case 'table_list':
        return <Database className="w-4 h-4 text-blue-400" />;
      case 'schema_info':
        return <FileText className="w-4 h-4 text-purple-400" />;
      case 'sql_result':
      case 'tabular_data':
        return <Table className="w-4 h-4 text-green-400" />;
      default:
        return <Eye className="w-4 h-4 text-gray-400" />;
    }
  };

  const getResultColor = () => {
    if (!observation.success) {
      return 'border-red-500/30 bg-red-900/10';
    }
    
    switch (observation.result_type) {
      case 'table_list':
        return 'border-blue-500/30 bg-blue-900/10';
      case 'schema_info':
        return 'border-purple-500/30 bg-purple-900/10';
      case 'sql_result':
      case 'tabular_data':
        return 'border-green-500/30 bg-green-900/10';
      default:
        return 'border-gray-500/30 bg-gray-900/10';
    }
  };

  const formatResult = (result: string) => {
    // Try to format table-like data
    if (observation.result_type === 'tabular_data' && result.includes('|')) {
      return result; // Keep table formatting
    }
    
    // For table lists, format as comma-separated with line breaks
    if (observation.result_type === 'table_list') {
      return result.split(',').map(table => table.trim()).join('\n');
    }
    
    return result;
  };

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(observation.result);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
    }
  };

  const isTableData = observation.result_type === 'tabular_data' || 
                     (observation.result_type === 'sql_result' && observation.result.includes('|'));
  
  const resultLines = observation.result.split('\n');
  const isLongResult = resultLines.length > 5 || observation.result.length > 200;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`border rounded-lg ${getResultColor()}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-gray-600/30">
        <div className="flex items-center gap-2">
          {getResultIcon()}
          <span className="text-sm font-medium text-white">Result</span>
          {observation.success ? (
            <CheckCircle className="w-4 h-4 text-green-400" />
          ) : (
            <AlertCircle className="w-4 h-4 text-red-400" />
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Copy Button */}
          <button
            onClick={copyToClipboard}
            className="p-1 hover:bg-white/10 rounded text-gray-400 hover:text-white transition-colors duration-200"
            title="Copy result"
          >
            <Copy className="w-3 h-3" />
          </button>

          {/* Expand/Collapse for long results */}
          {isLongResult && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors duration-200"
            >
              <span>{isExpanded ? 'Collapse' : 'Expand'}</span>
              {isExpanded ? 
                <ChevronUp className="w-3 h-3" /> : 
                <ChevronDown className="w-3 h-3" />
              }
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="p-3">
        {copied && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="mb-2 text-xs text-green-400 bg-green-900/20 px-2 py-1 rounded"
          >
            Copied to clipboard!
          </motion.div>
        )}

        <div className={`sql-container ${isLongResult && !isExpanded ? 'max-h-32 overflow-hidden' : ''}`}>
          {isTableData ? (
            <div className="font-mono text-sm">
              {resultLines.map((line, index) => {
                if (index === 0 || (index === 1 && line.includes('-'))) {
                  // Header row or separator
                  return (
                    <div key={index} className="text-blue-300 font-semibold border-b border-gray-600/30 pb-1 mb-1">
                      {line}
                    </div>
                  );
                }
                return (
                  <div key={index} className="text-gray-300 py-0.5">
                    {line}
                  </div>
                );
              })}
            </div>
          ) : (
            <pre className="text-sm text-gray-300 whitespace-pre-wrap break-words">
              {formatResult(observation.result)}
            </pre>
          )}
        </div>

        {/* Fade overlay for collapsed long results */}
        {isLongResult && !isExpanded && (
          <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-current to-transparent pointer-events-none opacity-20" />
        )}

        {/* Result Metadata */}
        <div className="flex items-center justify-between mt-3 pt-2 border-t border-gray-600/30 text-xs text-gray-500">
          <span>Type: {observation.result_type.replace('_', ' ')}</span>
          <span>
            {observation.result.length > 1000 
              ? `${(observation.result.length / 1000).toFixed(1)}K chars`
              : `${observation.result.length} chars`
            }
          </span>
        </div>
      </div>
    </motion.div>
  );
}