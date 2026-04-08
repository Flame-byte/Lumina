/**
 * Lumina Agent Backend API Type Definitions
 *
 * These types match the backend FastAPI Pydantic models
 */

// ========== Backend API Response Types ==========

/**
 * Task item (Planner planning result)
 */
export interface TodoItem {
  id: string;
  description: string;
  tool: string;
}

/**
 * Tool item
 */
export interface ToolItem {
  name: string;
  description: string;
}

/**
 * Interrupt information (HITL waiting for confirmation)
 */
export interface InterruptInfo {
  todo_list: TodoItem[];
  tool_list: ToolItem[];
}

/**
 * Chat response status
 */
export type ChatStatus = "completed" | "interrupted" | "pending_confirmation";

/**
 * Chat response (/api/chat)
 */
export interface ChatResponse {
  thread_id: string;
  status: ChatStatus;
  todo_list?: TodoItem[];
  tool_list?: ToolItem[];
  interrupt_info?: InterruptInfo;
  result?: {
    execution_results?: any;
  };
  messages?: {
    id: string;
    type: "human" | "ai";
    content: string;
    metadata?: Record<string, any>;
  }[];
  error_message?: string;
}

/**
 * Confirm response (/api/confirm)
 */
export interface ConfirmResponse {
  thread_id: string;
  status: "completed";
  result?: {
    execution_results?: any;
  };
  messages?: {
    id: string;
    type: "human" | "ai";
    content: string;
    metadata?: Record<string, any>;
  }[];
}

/**
 * Reject response (/api/reject)
 */
export interface RejectResponse {
  thread_id: string;
  status: "completed" | "pending_confirmation";
  result?: {
    todo_list?: TodoItem[];
    tool_list?: ToolItem[];
    execution_results?: any;
  };
  messages?: {
    id: string;
    type: "human" | "ai";
    content: string;
    metadata?: Record<string, any>;
  }[];
}

/**
 * Session information
 */
export interface SessionInfo {
  id: string;
  title?: string;
  created_at?: string;
  updated_at?: string;
  status?: string;
}

/**
 * Session list response (/api/sessions)
 */
export interface SessionsResponse {
  sessions: SessionInfo[];
}

/**
 * Status response (/api/status/{thread_id})
 */
export interface StatusResponse {
  thread_id: string;
  todo_list?: TodoItem[];
  tool_list?: ToolItem[];
  execution_results?: any;
  has_pending_interrupt: boolean;
}

/**
 * Load session response (/api/session/{session_id}/load)
 */
export interface LoadSessionResponse {
  thread_id: string | null;
  session_id: string;
  loaded_message_count: number;
}

/**
 * File metadata
 */
export interface FileMetadata {
  id: string;
  original_filename: string;
  file_type: string;
  processed_type: string;
  storage_path?: string;
  created_at: string;
}

/**
 * Get session files response (/api/session/{session_id}/files)
 */
export interface SessionFilesResponse {
  session_id: string;
  metadata: FileMetadata[];
}

/**
 * Upload files response (/api/upload)
 */
export interface UploadResponse {
  session_id: string;
  processed_items: {
    id: string;
    type: string;
    filename: string;
  }[];
}

/**
 * Delete session response (/api/session/{session_id})
 */
export interface DeleteSessionResponse {
  status: "deleted";
  session_id: string;
  deleted_items: number;
}

/**
 * Health check response (/api/health)
 */
export interface HealthResponse {
  status: "healthy";
  agent_initialized: boolean;
}

// ========== Frontend UI Message Types ==========

/**
 * UI message content block
 */
export interface ContentBlock {
  type: "text" | "image" | "file";
  text?: string;
  data_url?: string;
  filename?: string;
}

/**
 * UI message (for frontend rendering)
 */
export interface UIMessage {
  id: string;
  type: "human" | "ai";
  content: string | ContentBlock[];
  timestamp?: number;
  files?: string[];
}

// ========== Request Types ==========

/**
 * Chat request
 */
export interface ChatRequest {
  message: string;
  files?: string[];
  thread_id?: string;
  session_id?: string;
}

/**
 * Confirm request
 */
export interface ConfirmRequest {
  thread_id: string;
}

/**
 * Reject request
 */
export interface RejectRequest {
  thread_id: string;
  feedback: string;
}

// ========== HITL Types (for frontend display) ==========

/**
 * HITL action request (for frontend display)
 */
export interface ActionRequest {
  task_id: string;
  description: string;
  tool: string;
}

/**
 * HITL review config
 */
export interface ReviewConfig {
  action_name: string;
  allowed_decisions: ("approve" | "reject")[];
}

/**
 * HITL request (for frontend display, matches backend InterruptInfo)
 */
export interface FrontendHITLRequest {
  action_requests: ActionRequest[];
  review_configs: ReviewConfig[];
}

// ========== Config Management Types ==========

/**
 * Get config response (/api/config)
 */
export interface ConfigGetResponse {
  llm: Record<string, any>;
  agent: Record<string, any>;
}

/**
 * Update config request
 */
export interface ConfigUpdateRequest {
  llm?: Record<string, any>;
  agent?: Record<string, any>;
}

/**
 * Update config response
 */
export interface ConfigUpdateResponse {
  status: string;
  llm?: Record<string, any>;
  agent?: Record<string, any>;
}
