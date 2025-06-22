// src/components/Chat/ChatController.tsx

import { useEffect } from 'react';
import { useChatInternal } from '@/context/ChatContext';
import { useChatController } from '@/hooks/useChatController';

/**
 * ChatController is a headless component that connects the streaming
 * functionality with the ChatContext. It doesn't render anything.
 */
export function ChatController() {
  const { sendMessage, stopStreaming } = useChatController();
  const { registerSendMessage, registerStopStreaming } = useChatInternal();

  useEffect(() => {
    // Register the streaming functions with the context
    registerSendMessage(sendMessage);
    registerStopStreaming(stopStreaming);

    // Cleanup on unmount
    return () => {
      registerSendMessage(() => {});
      registerStopStreaming(() => {});
    };
  }, [sendMessage, stopStreaming, registerSendMessage, registerStopStreaming]);

  // This component doesn't render anything
  return null;
}