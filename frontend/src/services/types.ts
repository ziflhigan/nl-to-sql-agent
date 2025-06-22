// src/services/types.ts

export interface StreamEvent {
  type: string;
  timestamp: string;
  [key: string]: any;
}

export interface ExecutionStartEvent extends StreamEvent {
  type: 'execution_start';
  question: string;
  query_id: string;
}

export interface AgentActionEvent extends StreamEvent {
  type: 'agent_action';
  step_number: number;
  thought?: string;
  action: {
    tool: string;
    category: 'schema_exploration' | 'data_retrieval' | 'validation' | 'unknown';
    description: string;
    purpose: string;
    input: string;
    raw_input: string;
  };
}

export interface AgentObservationEvent extends StreamEvent {
  type: 'agent_observation';
  step_number: number;
  observation: {
    result: string;
    result_type: 'table_list' | 'schema_info' | 'sql_result' | 'tabular_data' | 'validation_result' | 'text' | 'empty';
    success: boolean;
  };
}

export interface AgentFinishEvent extends StreamEvent {
  type: 'agent_finish';
  final_answer: string;
  total_steps: number;
}

export interface ExecutionSummaryEvent extends StreamEvent {
  type: 'execution_summary';
  execution_time: number;
  success: boolean;
}

export interface ExecutionCompleteEvent extends StreamEvent {
  type: 'execution_complete';
}

export interface HeartbeatEvent extends StreamEvent {
  type: 'heartbeat';
}

export interface ErrorEvent extends StreamEvent {
  type: 'error';
  error: {
    message: string;
    type: string;
  };
}

export type ChatStreamEvent = 
  | ExecutionStartEvent
  | AgentActionEvent
  | AgentObservationEvent
  | AgentFinishEvent
  | ExecutionSummaryEvent
  | ExecutionCompleteEvent
  | HeartbeatEvent
  | ErrorEvent;

export interface ReActStep {
  step_number: number;
  thought?: string;
  action: AgentActionEvent['action'];
  observation?: AgentObservationEvent['observation'];
  timestamp: string;
}

export interface ChatMessage {
  id: string;
  question: string;
  answer?: string;
  steps: ReActStep[];
  status: 'thinking' | 'processing' | 'completed' | 'error';
  execution_time?: number;
  timestamp: string;
  error_message?: string;
}

export interface ChatState {
  messages: ChatMessage[];
  currentMessage: ChatMessage | null;
  isStreaming: boolean;
  error: string | null;
}

export interface ChatContextType extends ChatState {
  sendMessage: (question: string) => void;
  clearMessages: () => void;
  stopStreaming: () => void;
}

export interface ApiResponse<T = any> {
  data: T | null;
  error: {
    code: number;
    message: string;
    type: string;
  } | null;
  success: boolean;
  timestamp: string;
}

// Animation types
export interface AnimationVariants {
  hidden: any;
  visible: any;
  exit?: any;
}

// Component prop types
export interface ThoughtBubbleProps {
  thought: string;
  stepNumber: number;
  isVisible: boolean;
}

export interface ActionCardProps {
  action: AgentActionEvent['action'];
  stepNumber: number;
  thought?: string;
  isCompleted: boolean;
}

export interface ObservationPanelProps {
  observation: AgentObservationEvent['observation'];
  stepNumber: number;
}

export interface SQLHighlighterProps {
  sql: string;
  animated?: boolean;
}

export interface ProgressIndicatorProps {
  currentStep: number;
  totalSteps?: number;
  isComplete: boolean;
}

export interface FinalAnswerProps {
  answer: string;
  totalSteps: number;
  executionTime?: number;
  onNewQuestion: () => void;
}

// Connection status
export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface ConnectionState {
  status: ConnectionStatus;
  error?: string;
  lastHeartbeat?: Date;
}