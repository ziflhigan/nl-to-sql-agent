// src/App.tsx

import * as React from 'react';
import { ChatProvider } from '@/context/ChatContext';
import { ChatController } from '@/components/Chat/ChatController';
import { ChatContainer } from '@/components/Chat/ChatContainer';
import { Header } from '@/components/Layout/Header';
import { ErrorBoundary } from '@/components/UI/ErrorBoundary';
import '@/styles/globals.css';

function App() {
  return (
    <ErrorBoundary>
      <ChatProvider>
        <ChatController />
        <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
          <Header />
          <main className="container mx-auto px-4 py-8">
            <ChatContainer />
          </main>
        </div>
      </ChatProvider>
    </ErrorBoundary>
  );
}

export default App;