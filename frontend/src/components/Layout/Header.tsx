// src/components/Layout/Header.tsx

import * as React from 'react';
import { Database, Sparkles, Github, Brain } from 'lucide-react';

export function Header() {
  return (
    <header className="border-b border-white/10 bg-dark-900/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          {/* Logo and Title */}
          <div className="flex items-center gap-3">
            <div className="relative">
              <Database className="w-8 h-8 text-blue-400" />
              <Sparkles className="w-4 h-4 text-purple-400 absolute -top-1 -right-1" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gradient">
                NL-to-SQL Agent
              </h1>
              <p className="text-sm text-gray-400">
                Ask questions in natural language
              </p>
            </div>
          </div>

          {/* Features Badge */}
          <div className="hidden md:flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1 bg-blue-500/10 border border-blue-500/20 rounded-full text-sm text-blue-300">
              <Brain className="w-4 h-4" />
              Real-time ReAct Loop
            </div>
            
            {/* GitHub Link */}
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 hover:bg-white/5 rounded-lg transition-colors duration-200"
              aria-label="View on GitHub"
            >
              <Github className="w-5 h-5 text-gray-400 hover:text-white" />
            </a>
          </div>

          {/* Mobile Menu */}
          <div className="md:hidden">
            <div className="flex items-center gap-2 px-2 py-1 bg-blue-500/10 border border-blue-500/20 rounded-lg text-xs text-blue-300">
              <Brain className="w-3 h-3" />
              AI Powered
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}