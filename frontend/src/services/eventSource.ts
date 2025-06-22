// src/services/eventSource.ts

import { ChatStreamEvent, ConnectionStatus } from './types';

export class StreamingService {
  private eventSource: EventSource | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 3;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private onEventCallback?: (event: ChatStreamEvent) => void;
  private onStatusChangeCallback?: (status: ConnectionStatus, error?: string) => void;
  private currentQuestion: string | null = null;

  constructor() {
    this.handleBeforeUnload = this.handleBeforeUnload.bind(this);
    window.addEventListener('beforeunload', this.handleBeforeUnload);
  }

  public async startStream(
    question: string,
    onEvent: (event: ChatStreamEvent) => void,
    onStatusChange?: (status: ConnectionStatus, error?: string) => void
  ): Promise<void> {
    this.onEventCallback = onEvent;
    this.onStatusChangeCallback = onStatusChange;
    this.currentQuestion = question;

    try {
      this.closeExistingConnection();
      this.notifyStatusChange('connecting');

      // Create EventSource connection
      const eventSource = new EventSource('/api/v1/chat/stream');
      this.eventSource = eventSource;

      this.setupEventListeners();
      
      // Send the question via POST request
      await this.sendQuestion(question);
      
    } catch (error) {
      console.error('Failed to start stream:', error);
      this.notifyStatusChange('error', error instanceof Error ? error.message : 'Failed to start stream');
      throw error;
    }
  }

  private setupEventListeners(): void {
    if (!this.eventSource) return;

    this.eventSource.onopen = () => {
      console.log('SSE connection opened');
      this.notifyStatusChange('connected');
      this.reconnectAttempts = 0; // Reset on successful connection
    };

    this.eventSource.onmessage = (event) => {
      try {
        const data: ChatStreamEvent = JSON.parse(event.data);
        this.handleStreamEvent(data);
        
        // Reset reconnect attempts on successful message
        this.reconnectAttempts = 0;
      } catch (error) {
        console.error('Error parsing event data:', error);
        this.notifyError('Failed to parse server message');
      }
    };

    this.eventSource.onerror = (error) => {
      console.error('EventSource error:', error);
      this.handleConnectionError();
    };
  }

  private async sendQuestion(question: string): Promise<void> {
    try {
      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (error) {
      console.error('Failed to send question:', error);
      throw error;
    }
  }

  private handleStreamEvent(event: ChatStreamEvent): void {
    if (this.onEventCallback) {
      this.onEventCallback(event);
    }

    // Handle connection completion
    if (event.type === 'execution_complete') {
      this.closeConnection();
    }

    // Handle errors from the stream
    if (event.type === 'error') {
      this.notifyError(event.error?.message || 'Stream error occurred');
    }
  }

  private handleConnectionError(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), 10000); // Exponential backoff, max 10s
      
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay}ms`);
      this.notifyStatusChange('connecting', `Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

      this.reconnectTimeout = setTimeout(() => {
        if (this.currentQuestion) {
          this.reconnect();
        }
      }, delay);
    } else {
      this.notifyStatusChange('error', 'Connection failed after maximum retry attempts');
    }
  }

  private async reconnect(): Promise<void> {
    if (!this.currentQuestion || !this.onEventCallback) return;

    try {
      await this.startStream(this.currentQuestion, this.onEventCallback, this.onStatusChangeCallback);
    } catch (error) {
      console.error('Reconnection failed:', error);
      this.notifyStatusChange('error', 'Reconnection failed');
    }
  }

  private notifyStatusChange(status: ConnectionStatus, error?: string): void {
    if (this.onStatusChangeCallback) {
      this.onStatusChangeCallback(status, error);
    }
  }

  private notifyError(message: string): void {
    if (this.onEventCallback) {
      this.onEventCallback({
        type: 'error',
        timestamp: new Date().toISOString(),
        error: {
          message,
          type: 'client_error'
        }
      });
    }
  }

  public closeConnection(): void {
    this.clearReconnectTimeout();
    this.closeExistingConnection();
    this.notifyStatusChange('disconnected');
    this.currentQuestion = null;
  }

  private closeExistingConnection(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  private clearReconnectTimeout(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
  }

  private handleBeforeUnload(): void {
    this.closeConnection();
  }

  public getConnectionStatus(): ConnectionStatus {
    if (!this.eventSource) return 'disconnected';
    
    switch (this.eventSource.readyState) {
      case EventSource.CONNECTING:
        return 'connecting';
      case EventSource.OPEN:
        return 'connected';
      case EventSource.CLOSED:
        return 'disconnected';
      default:
        return 'error';
    }
  }

  public destroy(): void {
    this.closeConnection();
    window.removeEventListener('beforeunload', this.handleBeforeUnload);
  }
}

// Singleton instance
let streamingServiceInstance: StreamingService | null = null;

export function getStreamingService(): StreamingService {
  if (!streamingServiceInstance) {
    streamingServiceInstance = new StreamingService();
  }
  return streamingServiceInstance;
}

// Clean up singleton on hot reload (development)
// Using type-safe check for Vite's HMR API
declare const import_meta: {
  hot?: {
    dispose: (callback: () => void) => void;
  };
};

if (typeof import_meta !== 'undefined' && import_meta.hot) {
  import_meta.hot.dispose(() => {
    if (streamingServiceInstance) {
      streamingServiceInstance.destroy();
      streamingServiceInstance = null;
    }
  });
}