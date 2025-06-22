// src/hooks/useChatController.ts

import { useCallback, useEffect } from 'react';
import { useChatInternal } from '@/context/ChatContext';
import { ChatStreamEvent, ConnectionStatus } from '@/services/types';

export function useChatController() {
  // REMOVED: The old eventSource service is no longer needed.
  // const streamingService = useRef(getStreamingService()); 

  const {
    startStreaming,
    addStep,
    updateStep,
    setFinalAnswer,
    setError,
    clearError,
    completeMessage,
  } = useChatInternal();

  // Generate unique message ID
  const generateMessageId = useCallback(() => {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  // Process individual stream events (This function is now used by our new fetch logic)
  const handleStreamEvent = useCallback((event: ChatStreamEvent) => {
    console.log('Stream event:', event.type, event);

    switch (event.type) {
      case 'execution_start':
        clearError();
        break;
      case 'agent_action':
        addStep({
          step_number: event.step_number,
          thought: event.thought,
          action: event.action,
          timestamp: event.timestamp,
        });
        break;
      case 'agent_observation':
        updateStep(event.step_number, event.observation);
        break;
      case 'agent_finish':
        setFinalAnswer(event.final_answer, event.total_steps);
        break;
      case 'execution_summary':
        // Optional: Update execution time if needed
        break;
      case 'execution_complete':
        completeMessage();
        break;
      case 'heartbeat':
        // Keep-alive signal, no action needed
        break;
      case 'error':
        setError(event.message || 'An error occurred during processing');
        break;
      default:
        console.warn('Unknown event type:', (event as any).type);
    }
  }, [addStep, updateStep, setFinalAnswer, setError, clearError, completeMessage]);

  // Main function to send a message and start streaming
  // THIS IS THE REPLACEMENT LOGIC
  const sendMessage = useCallback(async (question: string) => {
    if (!question.trim()) {
      setError('Question cannot be empty');
      return;
    }
    
    const messageId = generateMessageId();
    startStreaming(question, messageId); // Dispatch action to show "thinking..." state

    try {
      const response = await fetch('http://localhost:5000/api/v1/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream'
        },
        body: JSON.stringify({ question }),
      });

      if (!response.ok || !response.body) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulatedData = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        accumulatedData += decoder.decode(value, { stream: true });
        const events = accumulatedData.split('\n\n');
        accumulatedData = events.pop() || "";

        for (const eventString of events) {
          if (eventString.startsWith('data:')) {
            const jsonString = eventString.substring(5).trim();
            try {
              const eventData = JSON.parse(jsonString);
              // Funnel the data into our existing event handler
              handleStreamEvent(eventData);
            } catch (e) {
              console.error("Failed to parse event data:", jsonString);
            }
          }
        }
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to connect to the server';
      console.error('Streaming failed:', errorMessage);
      handleStreamEvent({ type: 'error', message: errorMessage, request_id: '', error: { message: errorMessage, type: 'unknown' }, timestamp: new Date().toISOString() });
    } finally {
        // The 'execution_complete' event from the server will handle the final state change
    }
  }, [generateMessageId, startStreaming, handleStreamEvent, setError]);

  // The stopStreaming function is more complex with fetch and requires AbortController
  // For now, we will leave it as a no-op to fix the main issue.
  const stopStreaming = useCallback(() => {
    console.warn("stopStreaming is not implemented for fetch yet.");
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      // If you implement AbortController, you would call abort() here.
    };
  }, []);

  return {
    sendMessage,
    stopStreaming,
  };
}