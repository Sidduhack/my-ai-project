export interface Project {
  id: string;
  name: string;
  description: string | null;
  status: ProjectStatus;
  requirements: Record<string, any>;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export type ProjectStatus = 
  | 'created' 
  | 'planning' 
  | 'running' 
  | 'paused' 
  | 'completed' 
  | 'failed' 
  | 'cancelled';

export interface Task {
  id: string;
  project_id: string;
  agent_id: string;
  description: string;
  priority: TaskPriority;
  status: TaskStatus;
  dependencies: string[];
  input_data: Record<string, any> | null;
  output_data: Record<string, any> | null;
  assigned_model: string | null;
  retry_count: number;
  max_retries: number;
  error: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export type TaskStatus = 
  | 'pending' 
  | 'running' 
  | 'blocked' 
  | 'completed' 
  | 'failed' 
  | 'cancelled';

export type TaskPriority = 
  | 'low' 
  | 'normal' 
  | 'high' 
  | 'critical';

export interface Agent {
  id: string;
  type: string;
  name: string;
  role: string | null;
  description: string | null;
  system_prompt: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AgentTypeInfo {
  type: string;
  name: string;
}

export interface Model {
  id: string;
  provider: string;
  model_id: string;
  display_name: string;
  capabilities: string[];
  context_window: number;
  max_output_tokens: number;
  supports_streaming: boolean;
  supports_structured: boolean;
  supports_vision: boolean;
  supports_functions: boolean;
  enabled: boolean;
}

export interface ModelHealth {
  model_id: string;
  provider: string;
  state: 'healthy' | 'degraded' | 'cooldown';
  success_count: number;
  failure_count: number;
  consecutive_failures: number;
  avg_latency_ms: number;
  recent_avg_latency_ms: number;
  timeout_count: number;
  error_count: number;
  last_success_at: string | null;
  last_failure_at: string | null;
  cooldown_until: string | null;
  is_available: boolean;
}

export interface ModelScore {
  model_id: string;
  agent_type: string;
  reliability_score: number;
  latency_score: number;
  confidence_score: number;
  recency_score: number;
  specialization_score: number;
  priority_score: number;
  total_score: number;
  sample_count: number;
}

export interface ModelRoute {
  primary_model: string;
  fallback_models: string[];
  priority: number;
  enabled: boolean;
}

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  environment: string;
}

export interface ReadinessCheck {
  status: 'ready' | 'degraded';
  checks: Record<string, any>;
}

export interface Metrics {
  orchestrator: {
    queue: {
      pending: number;
      running: number;
      completed: number;
      failed: number;
    };
  };
  models: {
    health: {
      healthy: number;
      degraded: number;
      cooldown: number;
      total: number;
    };
    providers: string[];
  };
  scoring: {
    total_scored_pairs: number;
  };
}

export interface Event {
  id: string;
  type: string;
  payload: Record<string, any>;
  timestamp: string;
  correlation_id: string | null;
  source: string | null;
}

export interface ProjectStatusResponse {
  project_id: string;
  name: string;
  status: ProjectStatus;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  tasks: Task[];
  queue_status: {
    pending: number;
    running: number;
    completed: number;
    failed: number;
  };
}

export interface ProjectCreate {
  name: string;
  description?: string;
  requirements?: Record<string, any>;
}

export interface AgentCreate {
  type: string;
  name: string;
  description?: string;
  config?: Record<string, any>;
  system_prompt?: string;
}

export interface AgentMemory {
  key: string;
  value: Record<string, any>;
}

export interface WebSocketMessage {
  type: string;
  payload: any;
  timestamp: string;
}

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
}