/**
 * Session Management Hook
 *
 * Used to manage session list, switch sessions, load history
 */

import { useState, useCallback, useEffect, useMemo } from "react";
import { useQueryState } from "nuqs";
import { CustomAPIClient } from "@/providers/client";
import type { SessionInfo } from "@/types/api";
import type { Message } from "@/hooks/useChat";

interface UseSessionOptions {
  apiUrl?: string;
  apiKey?: string;
}

export interface UseSessionReturn {
  // Session list
  sessions: SessionInfo[];
  sessionsLoading: boolean;

  // Current session
  currentSession: SessionInfo | null;
  sessionId: string | null;
  threadId: string | null;

  // Operations
  loadSessions: () => Promise<void>;
  switchSession: (sessionId: string) => Promise<Message[]>;
  createSession: (title?: string) => Promise<string>;
  deleteSession: (sessionId: string) => Promise<void>;
  refreshSession: (sessionId: string) => Promise<void>;

  // State management
  setSessions: (sessions: SessionInfo[]) => void;
}

/**
 * Session Management Hook
 */
export function useSession(options: UseSessionOptions = {}): UseSessionReturn {
  const [apiUrl] = useQueryState("apiUrl", {
    defaultValue: "http://localhost:8000",
  });
  const [apiKey] = useQueryState("apiKey");
  const [sessionId, _setSessionId] = useQueryState("sessionId");
  const [threadId, _setThreadId] = useQueryState("threadId");

  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [currentSession, setCurrentSession] = useState<SessionInfo | null>(null);

  // Create API client (use useMemo to cache instance)
  const client = useMemo(
    () => new CustomAPIClient(
      options.apiUrl || apiUrl,
      options.apiKey || apiKey || undefined
    ),
    [options.apiUrl, apiUrl, options.apiKey, apiKey]
  );

  // Load session list
  const loadSessions = useCallback(async () => {
    setSessionsLoading(true);
    try {
      const sessionList = await client.getSessions();
      setSessions(sessionList);

      // If there is a current sessionId, find the corresponding session info
      // Note: using sessionList instead of sessions state here to avoid relying on external variables
    } catch (error) {
      console.error("Failed to load sessions:", error);
      setSessions([]);
    } finally {
      setSessionsLoading(false);
    }
  }, [client]);

  // Switch session
  const switchSession = useCallback(async (newSessionId: string): Promise<Message[]> => {
    try {
      // Call backend API to load session history to checkpoint
      const result = await client.loadSession(newSessionId);

      // Use thread_id returned by backend to get messages (ensure only getting messages from this thread, avoid duplicates)
      const messages = await client.getSessionMessages(newSessionId, result.thread_id || undefined);

      // Update sessionId and threadId
      _setSessionId(newSessionId);
      if (result.thread_id) {
        _setThreadId(result.thread_id);
      }

      // Update current session info
      const session = sessions.find(s => s.id === newSessionId);
      if (session) {
        setCurrentSession(session);
      }

      // Convert messages to frontend format
      return messages.map((msg: any) => {
        // Parse metadata field
        let metadata = msg.metadata;
        if (typeof metadata === 'string') {
          try {
            metadata = JSON.parse(metadata);
          } catch {
            metadata = {};
          }
        }

        return {
          id: msg.id,
          type: msg.role === "human" ? "human" : "ai",
          content: msg.content,
          timestamp: new Date(msg.created_at).getTime(),
          metadata: metadata || {},
        };
      });
    } catch (error) {
      console.error("Failed to switch session:", error);
      throw error;
    }
  }, [client, sessions, _setSessionId, _setThreadId]);

  // Create new session (via API)
  const createSession = useCallback(async (title?: string): Promise<string> => {
    try {
      // Call backend API to create session
      const sessionInfo = await client.createSession(title);
      const newSessionId = sessionInfo.id;

      return newSessionId;
    } catch (error) {
      console.error("Failed to create session:", error);
      throw error;
    }
  }, [client]);

  // Delete session
  const deleteSession = useCallback(async (sessionIdToDelete: string) => {
    try {
      await client.deleteSession(sessionIdToDelete);

      // Remove from list
      setSessions(prev => prev.filter(s => s.id !== sessionIdToDelete));

      // If deleting current session, clear current session
      if (sessionId === sessionIdToDelete) {
        _setSessionId(null);
        _setThreadId(null);
        setCurrentSession(null);
      }
    } catch (error) {
      console.error("Failed to delete session:", error);
      throw error;
    }
  }, [client, sessionId, _setSessionId, _setThreadId]);

  // Refresh session info
  const refreshSession = useCallback(async (sessionIdToRefresh: string) => {
    try {
      // Reload session list
      await loadSessions();

      // If this is current session, also load history messages
      if (sessionIdToRefresh === sessionId && threadId) {
        await client.loadSession(sessionIdToRefresh, threadId);
      }
    } catch (error) {
      console.error("Failed to refresh session:", error);
      throw error;
    }
  }, [client, sessionId, threadId, loadSessions]);

  // Load session list on initialization
  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // When sessionId changes, update currentSession
  useEffect(() => {
    if (sessionId && sessions.length > 0) {
      const session = sessions.find((s) => s.id === sessionId);
      if (session) {
        setCurrentSession(session);
      }
    }
  }, [sessionId, sessions]);

  return {
    // Session list
    sessions,
    sessionsLoading,

    // Current session
    currentSession,
    sessionId: sessionId || null,
    threadId: threadId || null,

    // Operations
    loadSessions,
    switchSession,
    createSession,
    deleteSession,
    refreshSession,

    // State management
    setSessions,
  };
}
