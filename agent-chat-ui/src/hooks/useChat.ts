/**
 * Chat Management Hook
 *
 * Used to manage conversation state, send messages, HITL confirm/reject
 */

import { useState, useMemo, useCallback, useEffect, useRef } from "react";
import { useQueryState } from "nuqs";
import { v4 as uuidv4 } from "uuid";
import { CustomAPIClient } from "@/providers/client";
import type {
  ChatResponse,
  ConfirmResponse,
  RejectResponse,
  TodoItem,
  ToolItem,
  UIMessage,
  ContentBlock,
  InterruptInfo,
} from "@/types/api";

// UI message types (for frontend rendering)
export type Message = {
  id: string;
  type: "human" | "ai";
  content: string | ContentBlock[];
  timestamp?: number;
  metadata?: Record<string, any>;
};

// Interrupt type (HITL)
export interface Interrupt {
  id: string;
  value: {
    action_requests: {
      name: string;
      args: {
        task_id: string;
        description: string;
        tool: string;
      };
      description: string;
    }[];
    review_configs: {
      action_name: string;
      allowed_decisions: ("approve" | "reject")[];
    }[];
  };
}

// State type
export type StateType = {
  messages: Message[];
  ui?: {
    type: "ui";
    id: string;
    content: any;
  }[];
};

// Stream Context type
export type UseChatReturn = {
  messages: Message[];
  isLoading: boolean;
  interrupt: Interrupt | null;
  error: any | null;
  threadId: string | null;
  values: StateType;
  submit: (
    data: { messages?: Message[]; context?: Record<string, any>; files?: File[] },
    options?: any
  ) => Promise<void>;
  stop: () => void;
  confirm: () => Promise<void>;
  reject: (feedback: string) => Promise<void>;
  setMessages: (messages: Message[] | ((prev: Message[]) => Message[])) => void;
};

/**
 * Extract text from content
 */
function extractText(content: any): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .filter((c: any) => c.type === "text")
      .map((c: any) => c.text)
      .join(" ");
  }
  return "";
}

/**
 * Format execution results as text
 */
function formatExecutionResults(results: any): string {
  if (typeof results === "string") return results;
  if (typeof results === "object" && results !== null) {
    // If todo_list and tool_list format, format as user-friendly text
    if (results.todo_list && Array.isArray(results.todo_list)) {
      const tasks = results.todo_list
        .map((todo: any) => `- [${todo.tool || "unknown"}] ${todo.description || ""}`)
        .join("\n");
      return `Task planning completed:\n${tasks}`;
    }
    // Handle execution_results (backend may return { status, results } format directly)
    if (results.execution_results) {
      const execResults = results.execution_results;
      if (execResults.status === "completed" && execResults.results) {
        const result_list = execResults.results;
        if (Array.isArray(result_list)) {
          const summaries = result_list.map((item: any) => {
            const task_id = item.task_id || "unknown";
            const status = item.status || "unknown";
            const result = item.result || "";
            return `- Task ${task_id} [${status}]: ${result}`;
          });
          return summaries.join("\n");
        }
      }
      return JSON.stringify(execResults, null, 2);
    }
    // Backend directly returns { status, results } format
    if (results.status && results.results) {
      if (results.status === "completed" || results.status === "in_progress") {
        const result_list = results.results;
        if (Array.isArray(result_list)) {
          const summaries = result_list.map((item: any) => {
            const task_id = item.task_id || "unknown";
            const status = item.status || "unknown";
            const result = item.result || "";
            return `Task ${task_id} [${status}]: ${result}`;
          });
          return summaries.join("\n");
        }
      }
      return JSON.stringify(results, null, 2);
    }
    return JSON.stringify(results, null, 2);
  }
  return String(results);
}

/**
 * Convert backend interrupt format to frontend Interrupt format
 */
function convertInterruptToFormat(backendInterrupt: InterruptInfo): Interrupt {
  // Convert todo_list to action_requests
  const actionRequests = backendInterrupt.todo_list.map((todo) => ({
    name: "execute_task",
    args: {
      task_id: todo.id,
      description: todo.description,
      tool: todo.tool,
    },
    description: `Execute task: ${todo.description}`,
  }));

  // Create review_config
  const reviewConfigs = [
    {
      action_name: "execute_task",
      allowed_decisions: ["approve" as const, "reject" as const],
    },
  ];

  return {
    id: uuidv4(),
    value: {
      action_requests: actionRequests,
      review_configs: reviewConfigs,
    },
  };
}

/**
 * Chat management hook - replaces the original useStream
 */
export function useChat(): UseChatReturn {
  const [apiUrl] = useQueryState("apiUrl", {
    defaultValue: "http://localhost:8000",
  });
  const [apiKey] = useQueryState("apiKey");
  const [threadId, _setThreadId] = useQueryState("threadId");
  const [sessionId] = useQueryState("sessionId");

  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [interrupt, setInterrupt] = useState<Interrupt | null>(null);
  const [error, setError] = useState<any | null>(null);
  const [values, setValues] = useState<StateType>({ messages: [] });

  // Ref for stopping requests
  const abortControllerRef = useRef<AbortController | null>(null);
  // Ref for storing files to be uploaded
  const pendingFilesRef = useRef<File[]>([]);

  const client = useMemo(() => {
    return new CustomAPIClient(apiUrl, apiKey || undefined);
  }, [apiUrl, apiKey]);

  // Stop request
  const stop = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
  }, []);

  // Submit message
  const submit = useCallback(
    async (
      data: { messages?: Message[]; context?: Record<string, any>; files?: File[] },
      options?: any
    ) => {
      if (!client) {
        setError(new Error("API client not initialized - please check your API URL"));
        return;
      }

      // If there's already a request in progress, stop it first
      stop();

      // Create new AbortController
      abortControllerRef.current = new AbortController();

      setIsLoading(true);
      setError(null);

      try {
        // Get the last user message
        const lastMessage = data.messages?.[data.messages.length - 1];
        if (!lastMessage) {
          throw new Error("No message to send");
        }

        const text = extractText(lastMessage.content);

        // Handle file upload
        let uploadedFileIds: string[] | undefined;
        const filesToUpload = data.files || pendingFilesRef.current;

        if (filesToUpload && filesToUpload.length > 0) {
          // Upload files to backend first
          const uploadSessionId = data.context?.session_id || sessionId || undefined;
          const uploadResponse = await client.uploadFiles(uploadSessionId, filesToUpload);

          // Get the list of file IDs after upload
          uploadedFileIds = uploadResponse.processed_items.map(item => item.id);

          // Clear pending files
          pendingFilesRef.current = [];
        }

        // Send message (with file ID list)
        const response = await client.sendMessage(
          text,
          uploadedFileIds,
          threadId || undefined,
          data.context?.session_id || sessionId || undefined
        );

        // Update threadId
        if (response.thread_id && response.thread_id !== threadId) {
          _setThreadId(response.thread_id);
        }

        // Handle response
        if (response.status === "interrupted" || response.status === "pending_confirmation") {
          // Interrupt state - convert to frontend format
          if (response.interrupt_info) {
            const formattedInterrupt = convertInterruptToFormat(response.interrupt_info);
            setInterrupt(formattedInterrupt);

            // Also save raw backend interrupt info to values
            setValues({
              messages: [...messages, lastMessage],
              ui: [{
                type: "ui",
                id: uuidv4(),
                content: response.interrupt_info
              }]
            });
          }
          // Update messages
          setMessages((prev) => [...prev, lastMessage]);
        } else if (response.status === "completed") {
          // Completed state
          setInterrupt(null);

          // If backend returned messages, use backend returned messages (for multi-turn conversation)
          if (response.messages && response.messages.length > 0) {
            // Convert backend message format to frontend format
            const formattedMessages: Message[] = response.messages.map((msg: any) => ({
              id: msg.id || uuidv4(),
              type: msg.type as "human" | "ai",
              content: msg.content,
              metadata: msg.metadata || {},
            }));

            // Deduplicate merge: keep existing messages, add new messages (avoid duplicates)
            setMessages((prev) => {
              const existingIds = new Set(prev.map(m => m.id));
              const newMessages = formattedMessages.filter(m => !existingIds.has(m.id));
              return [...prev, ...newMessages];
            });
          } else {
            // Otherwise, only add current user message
            setMessages((prev) => [...prev, lastMessage]);
          }

          // If there are execution results, add to messages
          if (response.result) {
            const resultText = formatExecutionResults(response.result);
            const aiMessage: Message = {
              id: uuidv4(),
              type: "ai",
              content: resultText,
            };
            setMessages((prev) => {
              // Avoid duplicate addition
              const existingIds = new Set(prev.map(m => m.id));
              if (existingIds.has(aiMessage.id)) {
                return prev;
              }
              return [...prev, aiMessage];
            });
            setValues({
              messages: [...messages, lastMessage, aiMessage],
              ui: []
            });
          }
        } else if (response.status === "error") {
          throw new Error(response.error_message || "Unknown error");
        }
      } catch (err: any) {
        if (err.name === "AbortError") {
          // Request was cancelled, no error handling needed
          return;
        }
        setError(err);
        setInterrupt(null);
      } finally {
        setIsLoading(false);
        abortControllerRef.current = null;
      }
    },
    [client, threadId, sessionId, _setThreadId, stop, messages]
  );

  // Confirm execution (HITL approve)
  const confirm = useCallback(async () => {
    if (!client || !threadId) {
      setError(new Error("Cannot confirm: client or threadId not initialized"));
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await client.confirm(threadId);

      // If backend returned messages, use backend returned messages (deduplicate merge)
      if (response.messages && response.messages.length > 0) {
        // Convert backend message format to frontend format
        const formattedMessages: Message[] = response.messages.map((msg: any) => ({
          id: msg.id || uuidv4(),
          type: msg.type as "human" | "ai",
          content: msg.content,
          metadata: msg.metadata || {},
        }));

        // Deduplicate merge: keep existing messages, add new messages (avoid duplicates)
        setMessages((prev) => {
          const existingIds = new Set(prev.map(m => m.id));
          const newMessages = formattedMessages.filter(m => !existingIds.has(m.id));
          return [...prev, ...newMessages];
        });
      }

      // If there are execution results, add to messages
      if (response.result) {
        const resultText = formatExecutionResults(response.result);
        const aiMessage: Message = {
          id: uuidv4(),
          type: "ai",
          content: resultText,
        };
        setMessages((prev) => {
          // Avoid duplicate addition
          const existingIds = new Set(prev.map(m => m.id));
          if (existingIds.has(aiMessage.id)) {
            return prev;
          }
          return [...prev, aiMessage];
        });
      }

      // Clear interrupt
      setInterrupt(null);
    } catch (err: any) {
      setError(err);
    } finally {
      setIsLoading(false);
    }
  }, [client, threadId]);

  // Reject execution (HITL reject)
  const reject = useCallback(async (feedback: string) => {
    if (!client || !threadId) {
      setError(new Error("Cannot reject: client or threadId not initialized"));
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await client.reject(threadId, feedback);

      // If backend returned messages, use backend returned messages (deduplicate merge)
      if (response.messages && response.messages.length > 0) {
        // Convert backend message format to frontend format
        const formattedMessages: Message[] = response.messages.map((msg: any) => ({
          id: msg.id || uuidv4(),
          type: msg.type as "human" | "ai",
          content: msg.content,
          metadata: msg.metadata || {},
        }));

        // Deduplicate merge: keep existing messages, add new messages (avoid duplicates)
        setMessages((prev) => {
          const existingIds = new Set(prev.map(m => m.id));
          const newMessages = formattedMessages.filter(m => !existingIds.has(m.id));
          return [...prev, ...newMessages];
        });
      }

      // If re-planning (pending_confirmation), need to show interrupt again
      if (response.status === "pending_confirmation" && response.result) {
        const interruptInfo = response.result;
        if (interruptInfo.todo_list) {
          const formattedInterrupt = convertInterruptToFormat({
            todo_list: interruptInfo.todo_list,
            tool_list: interruptInfo.tool_list || []
          });
          setInterrupt(formattedInterrupt);

          // Add AI message to indicate feedback received and re-planning
          const aiMessage: Message = {
            id: uuidv4(),
            type: "ai",
            content: "Feedback received, re-planning...",
          };
          setMessages((prev) => [...prev, aiMessage]);
        }
      } else if (response.status === "completed" && response.result) {
        // Completed state, add AI message
        const resultText = formatExecutionResults(response.result);
        const aiMessage: Message = {
          id: uuidv4(),
          type: "ai",
          content: resultText,
        };
        setMessages((prev) => {
          // Avoid duplicate addition
          const existingIds = new Set(prev.map(m => m.id));
          if (existingIds.has(aiMessage.id)) {
            return prev;
          }
          return [...prev, aiMessage];
        });
        setInterrupt(null);
      }
    } catch (err: any) {
      setError(err);
    } finally {
      setIsLoading(false);
    }
  }, [client, threadId]);

  return {
    messages,
    isLoading,
    interrupt,
    error,
    threadId: threadId || null,
    values,
    submit,
    stop,
    confirm,
    reject,
    setMessages,
  };
}
