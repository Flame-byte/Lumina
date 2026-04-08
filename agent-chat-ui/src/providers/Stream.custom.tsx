/**
 * Custom Stream Hook - For communicating with Lumina Agent backend
 *
 * This file replaces the original LangGraph SDK Stream, using custom API client
 */

import { useState, useMemo, useCallback, useRef, createContext, useContext, ReactNode } from "react";
import { useQueryState } from "nuqs";
import { Message } from "@langchain/langgraph-sdk";
import { v4 as uuidv4 } from "uuid";
import { CustomAPIClient } from "./client";
import {
  convertInterruptToSDKFormat,
  type BackendInterrupt,
} from "@/lib/api-adapter";
import { HITLRequest } from "@/components/thread/agent-inbox/types";
import { Interrupt } from "@langchain/langgraph-sdk";

// UI message type
export type UIMessage = {
  type: "ui";
  id: string;
  content: any;
};

export type RemoveUIMessage = {
  type: "remove_ui";
  id: string;
};

// State type
export type StateType = {
  messages: Message[];
  ui?: UIMessage[];
};

// Stream Context type
export type StreamContextType = {
  messages: Message[];
  isLoading: boolean;
  interrupt: Interrupt<HITLRequest> | Interrupt<HITLRequest>[] | null;
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
};

const StreamContext = createContext<StreamContextType | undefined>(undefined);

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
    // If it's todo_list and tool_list format, format as user-friendly text
    if (results.todo_list && Array.isArray(results.todo_list)) {
      const tasks = results.todo_list.map((todo: any) =>
        `- [${todo.tool || "unknown"}] ${todo.description || ""}`
      ).join("\n");
      return `Task planning completed:\n${tasks}`;
    }
    return JSON.stringify(results, null, 2);
  }
  return String(results);
}

/**
 * Custom Stream Hook - Replaces LangGraph SDK's useStream
 */
function useCustomStreamLogic(): StreamContextType {
  const [apiUrl] = useQueryState("apiUrl", {
    defaultValue: "http://localhost:8000",
  });
  const [apiKey] = useQueryState("apiKey");
  const [threadId, setThreadId] = useQueryState("threadId");
  const [sessionId] = useQueryState("sessionId");

  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [interrupt, setInterrupt] = useState<
    Interrupt<HITLRequest> | Interrupt<HITLRequest>[] | null
  >(null);
  const [error, setError] = useState<any | null>(null);
  const [values, setValues] = useState<StateType>({ messages: [] });

  // Ref for stopping requests
  const abortControllerRef = useRef<AbortController | null>(null);
  // Ref for storing files to be uploaded
  const pendingFilesRef = useRef<File[]>([]);

  const client = useMemo(() => {
    if (!apiUrl) return null;
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
          data.context?.session_id
        );

        // Update threadId
        if (response.thread_id && response.thread_id !== threadId) {
          setThreadId(response.thread_id);
        }

        // Handle response
        if (response.status === "interrupted" || response.status === "pending_confirmation") {
          // Interrupt state - convert to SDK format
          if (response.interrupt_info) {
            const sdkInterrupt = convertInterruptToSDKFormat(response.interrupt_info);
            setInterrupt(sdkInterrupt);

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
          setMessages((prev) => [...prev, lastMessage]);

          // If there are execution results, add to messages
          if (response.result) {
            const resultText = formatExecutionResults(response.result);
            const aiMessage: Message = {
              id: uuidv4(),
              type: "ai",
              content: resultText,
            };
            setMessages((prev) => [...prev, aiMessage]);
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
    [client, threadId, setThreadId, stop, messages]
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

      // Update messages
      if (response.result) {
        const resultText = formatExecutionResults(response.result);
        const aiMessage: Message = {
          id: uuidv4(),
          type: "ai",
          content: resultText,
        };
        setMessages((prev) => [...prev, aiMessage]);
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

      // If re-planning (pending_confirmation), need to show interrupt again
      if (response.status === "pending_confirmation" && response.result) {
        const interruptInfo = response.result;
        if (interruptInfo.todo_list) {
          const sdkInterrupt = convertInterruptToSDKFormat({
            todo_list: interruptInfo.todo_list,
            tool_list: interruptInfo.tool_list || []
          });
          setInterrupt(sdkInterrupt);
        }
      } else if (response.status === "completed" && response.result) {
        // Completed state, add AI message
        const resultText = formatExecutionResults(response.result);
        const aiMessage: Message = {
          id: uuidv4(),
          type: "ai",
          content: resultText,
        };
        setMessages((prev) => [...prev, aiMessage]);
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
  };
}

// Provider component
export const StreamProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => {
  const stream = useCustomStreamLogic();
  return <StreamContext.Provider value={stream}>{children}</StreamContext.Provider>;
};

// Export Hook
export const useStreamContext = (): StreamContextType => {
  const context = useContext(StreamContext);
  if (context === undefined) {
    throw new Error("useStreamContext must be used within a StreamProvider");
  }
  return context;
};

// Also export useCustomStream as alternative name
export const useCustomStream = useCustomStreamLogic;

export default StreamContext;
