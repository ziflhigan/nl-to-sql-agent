// src/context/ChatContext.tsx

import * as React from 'react';
import { createContext, useContext, useReducer, useCallback, ReactNode, useRef } from 'react';
import { ChatState, ChatContextType, ChatMessage, ReActStep, ChatStreamEvent } from '@/services/types';

// Initial state
const initialState: ChatState = {
  messages: [],
  currentMessage: null,
  isStreaming: false,
  error: null,
};

// Action types
type ChatAction =
  | { type: 'START_STREAMING'; payload: { question: string; messageId: string } }
  | { type: 'STOP_STREAMING' }
  | { type: 'ADD_STEP'; payload: { step: ReActStep } }
  | { type: 'UPDATE_STEP'; payload: { stepNumber: number; observation: any } }
  | { type: 'SET_FINAL_ANSWER'; payload: { answer: string; totalSteps: number; executionTime?: number } }
  | { type: 'SET_ERROR'; payload: { error: string } }
  | { type: 'CLEAR_ERROR' }
  | { type: 'CLEAR_MESSAGES' }
  | { type: 'COMPLETE_MESSAGE' };

// Reducer
function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'START_STREAMING': {
      const newMessage: ChatMessage = {
        id: action.payload.messageId,
        question: action.payload.question,
        steps: [],
        status: 'thinking',
        timestamp: new Date().toISOString(),
      };

      return {
        ...state,
        currentMessage: newMessage,
        isStreaming: true,
        error: null,
      };
    }

    case 'STOP_STREAMING': {
      return {
        ...state,
        isStreaming: false,
      };
    }

    case 'ADD_STEP': {
      if (!state.currentMessage) return state;

      const updatedMessage = {
        ...state.currentMessage,
        steps: [...state.currentMessage.steps, action.payload.step],
        status: 'processing' as const,
      };

      return {
        ...state,
        currentMessage: updatedMessage,
      };
    }

    case 'UPDATE_STEP': {
      if (!state.currentMessage) return state;

      const updatedSteps = state.currentMessage.steps.map(step =>
        step.step_number === action.payload.stepNumber
          ? { ...step, observation: action.payload.observation }
          : step
      );

      const updatedMessage = {
        ...state.currentMessage,
        steps: updatedSteps,
      };

      return {
        ...state,
        currentMessage: updatedMessage,
      };
    }

    case 'SET_FINAL_ANSWER': {
      if (!state.currentMessage) return state;

      const completedMessage = {
        ...state.currentMessage,
        answer: action.payload.answer,
        status: 'completed' as const,
        execution_time: action.payload.executionTime,
      };

      return {
        ...state,
        currentMessage: completedMessage,
        messages: [...state.messages, completedMessage],
        isStreaming: false,
      };
    }

    case 'SET_ERROR': {
      let updatedMessage = state.currentMessage;
      
      if (updatedMessage) {
        updatedMessage = {
          ...updatedMessage,
          status: 'error' as const,
          error_message: action.payload.error,
        };
      }

      return {
        ...state,
        currentMessage: updatedMessage,
        error: action.payload.error,
        isStreaming: false,
        messages: updatedMessage ? [...state.messages, updatedMessage] : state.messages,
      };
    }

    case 'CLEAR_ERROR': {
      return {
        ...state,
        error: null,
      };
    }

    case 'CLEAR_MESSAGES': {
      return {
        ...initialState,
      };
    }

    case 'COMPLETE_MESSAGE': {
      if (!state.currentMessage) return state;

      return {
        ...state,
        currentMessage: null,
        isStreaming: false,
      };
    }

    default:
      return state;
  }
}

// Context
const ChatContext = createContext<ChatContextType | undefined>(undefined);

// Provider component
interface ChatProviderProps {
  children: ReactNode;
}

export function ChatProvider({ children }: ChatProviderProps) {
  const [state, dispatch] = useReducer(chatReducer, initialState);
  const sendMessageRef = useRef<((question: string) => void) | null>(null);
  const stopStreamingRef = useRef<(() => void) | null>(null);

  const sendMessage = useCallback((question: string) => {
    if (sendMessageRef.current) {
      sendMessageRef.current(question);
    } else {
      console.warn('Streaming service not ready');
    }
  }, []);

  const clearMessages = useCallback(() => {
    dispatch({ type: 'CLEAR_MESSAGES' });
  }, []);

  const stopStreaming = useCallback(() => {
    if (stopStreamingRef.current) {
      stopStreamingRef.current();
    }
    dispatch({ type: 'STOP_STREAMING' });
  }, []);

  const contextValue: ChatContextType = {
    ...state,
    sendMessage,
    clearMessages,
    stopStreaming,
  };

  // Expose internal functions for the streaming service
  const internalFunctions = {
    startStreaming: useCallback((question: string, messageId: string) => {
      dispatch({ type: 'START_STREAMING', payload: { question, messageId } });
    }, []),

    addStep: useCallback((step: ReActStep) => {
      dispatch({ type: 'ADD_STEP', payload: { step } });
    }, []),

    updateStep: useCallback((stepNumber: number, observation: any) => {
      dispatch({ type: 'UPDATE_STEP', payload: { stepNumber, observation } });
    }, []),

    setFinalAnswer: useCallback((answer: string, totalSteps: number, executionTime?: number) => {
      dispatch({ type: 'SET_FINAL_ANSWER', payload: { answer, totalSteps, executionTime } });
    }, []),

    setError: useCallback((error: string) => {
      dispatch({ type: 'SET_ERROR', payload: { error } });
    }, []),

    clearError: useCallback(() => {
      dispatch({ type: 'CLEAR_ERROR' });
    }, []),

    completeMessage: useCallback(() => {
      dispatch({ type: 'COMPLETE_MESSAGE' });
    }, []),

    // Functions to register external handlers
    registerSendMessage: useCallback((handler: (question: string) => void) => {
      sendMessageRef.current = handler;
    }, []),

    registerStopStreaming: useCallback((handler: () => void) => {
      stopStreamingRef.current = handler;
    }, []),
  };

  // Expose internal functions
  (contextValue as any)._internal = internalFunctions;

  return (
    <ChatContext.Provider value={contextValue}>
      {children}
    </ChatContext.Provider>
  );
}

// Custom hook to use the chat context
export function useChat() {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
}

// Custom hook for internal context functions (used by streaming service)
export function useChatInternal() {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error('useChatInternal must be used within a ChatProvider');
  }
  return (context as any)._internal;
}