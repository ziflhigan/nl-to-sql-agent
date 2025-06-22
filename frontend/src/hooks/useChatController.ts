// src/hooks/useChatController.ts

import { useCallback, useEffect, useRef } from 'react';
import { useChatInternal } from '@/context/ChatContext';
import { getStreamingService } from '@/services/eventSource';
import { ChatStreamEvent, ReActStep, ConnectionStatus } from '@/services/types';

export function useChatController() {
  const streamingService = useRef(getStreamingService());
  const {
    startStreaming,
    addStep,
    updateStep,
    setFinalAnswer,
    setError,
    clearError,
    completeMessage,
  } = useChatInternal();

  const currentStepsRef = useRef<Map<number, ReActStep>>(new Map());

  // Generate unique message ID
  const generateMessageId = useCallback(() => {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  // Process individual stream events
  const handleStreamEvent = useCallback((event: ChatStreamEvent) => {
    console.log('Stream event:', event.type, event);

    switch (event.type) {
      case 'execution_start':
        clearError();
        break;

      case 'agent_action':
        const newStep: ReActStep = {
          step_number: event.step_number,
          thought: event.thought,
          action: event.action,
          timestamp: event.timestamp,
        };

        currentStepsRef.current.set(event.step_number, newStep);
        addStep(newStep);
        break;

      case 'agent_observation':
        const existingStep = currentStepsRef.current.get(event.step_number);
        if (existingStep) {
          const updatedStep: ReActStep = {
            ...existingStep,
            observation: event.observation,
          };
          currentStepsRef.current.set(event.step_number, updatedStep);
          updateStep(event.step_number, event.observation);
        }
        break;

      case 'agent_finish':
        setFinalAnswer(event.final_answer, event.total_steps);
        break;

      case 'execution_summary':
        // Optional: Update execution time if needed
        break;

      case 'execution_complete':
        completeMessage();
        currentStepsRef.current.clear();
        break;

      case 'heartbeat':
        // Keep-alive signal, no action needed
        break;

      case 'error':
        setError(event.error?.message || 'An error occurred during processing');
        currentStepsRef.current.clear();
        break;

      default:
        console.warn('Unknown event type:', (event as any).type);
    }
  }, [addStep, updateStep, setFinalAnswer, setError, clearError, completeMessage]);

  // Handle connection status changes
  const handleStatusChange = useCallback((status: ConnectionStatus, error?: string) => {
    console.log('Connection status:', status, error);
    
    if (status === 'error') {
      setError(error || 'Connection error occurred');
    }
  }, [setError]);

  // Main function to send a message and start streaming
  const sendMessage = useCallback(async (question: string) => {
    if (!question.trim()) {
      setError('Question cannot be empty');
      return;
    }

    try {
      const messageId = generateMessageId();
      
      // Start the message in the context
      startStreaming(question, messageId);
      
      // Start the streaming service
      await streamingService.current.startStream(
        question,
        handleStreamEvent,
        handleStatusChange
      );
    } catch (error) {
      console.error('Failed to send message:', error);
      setError(error instanceof Error ? error.message : 'Failed to send message');
    }
  }, [generateMessageId, startStreaming, handleStreamEvent, handleStatusChange, setError]);

  // Stop streaming function
  const stopStreaming = useCallback(() => {
    streamingService.current.closeConnection();
    currentStepsRef.current.clear();
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      streamingService.current.closeConnection();
      currentStepsRef.current.clear();
    };
  }, []);

  return {
    sendMessage,
    stopStreaming,
  };
}