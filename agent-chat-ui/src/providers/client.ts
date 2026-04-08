/**
 * Custom API Client - For communicating with Lumina Agent backend
 */

import type {
  ChatResponse,
  ConfirmResponse,
  RejectResponse,
  UploadResponse,
  SessionFilesResponse,
  DeleteSessionResponse,
  LoadSessionResponse,
  SessionsResponse,
  StatusResponse,
  HealthResponse,
  SessionInfo,
  ConfigGetResponse,
  ConfigUpdateRequest,
  ConfigUpdateResponse,
} from "@/types/api";

export class CustomAPIClient {
  private baseUrl: string;
  private apiKey: string | undefined;

  constructor(apiUrl: string, apiKey?: string) {
    this.baseUrl = apiUrl;
    this.apiKey = apiKey;
  }

  /**
   * Send message to backend
   */
  async sendMessage(
    message: string,
    files?: string[],  // File ID list
    threadId?: string,
    sessionId?: string
  ): Promise<ChatResponse> {
    const body: any = { message };
    if (threadId) body.thread_id = threadId;
    if (sessionId) body.session_id = sessionId;
    if (files && files.length > 0) body.files = files;

    const response = await fetch(`${this.baseUrl}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(this.apiKey && {
          "X-Api-Key": this.apiKey,
        }),
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API request failed: ${response.status} - ${errorText}`);
    }

    return response.json();
  }

  /**
   * Confirm execution (HITL approve)
   */
  async confirm(threadId: string): Promise<ConfirmResponse> {
    const response = await fetch(`${this.baseUrl}/api/confirm`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(this.apiKey && {
          "X-Api-Key": this.apiKey,
        }),
      },
      body: JSON.stringify({ thread_id: threadId }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Confirm request failed: ${response.status} - ${errorText}`);
    }

    return response.json();
  }

  /**
   * Reject execution (HITL reject)
   */
  async reject(
    threadId: string,
    feedback: string
  ): Promise<RejectResponse> {
    const response = await fetch(`${this.baseUrl}/api/reject`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(this.apiKey && {
          "X-Api-Key": this.apiKey,
        }),
      },
      body: JSON.stringify({ thread_id: threadId, feedback }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Reject request failed: ${response.status} - ${errorText}`);
    }

    return response.json();
  }

  /**
   * Upload files
   */
  async uploadFiles(
    sessionId: string | undefined,
    files: File[]
  ): Promise<UploadResponse> {
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));

    const url = new URL(`${this.baseUrl}/api/upload`);
    if (sessionId) {
      url.searchParams.append("session_id", sessionId);
    }

    const response = await fetch(url.toString(), {
      method: "POST",
      headers: this.apiKey
        ? {
            "X-Api-Key": this.apiKey,
          }
        : undefined,
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Upload files failed: ${response.status} - ${errorText}`);
    }

    return response.json();
  }

  /**
   * Get session file metadata
   */
  async getSessionFiles(sessionId: string): Promise<SessionFilesResponse> {
    const response = await fetch(
      `${this.baseUrl}/api/session/${sessionId}/files`,
      {
        headers: this.apiKey
          ? {
              "X-Api-Key": this.apiKey,
            }
          : undefined,
      }
    );

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `Get session files failed: ${response.status} - ${errorText}`
      );
    }

    return response.json();
  }

  /**
   * Delete session
   */
  async deleteSession(sessionId: string): Promise<DeleteSessionResponse> {
    const response = await fetch(`${this.baseUrl}/api/session/${sessionId}`, {
      method: "DELETE",
      headers: this.apiKey
        ? {
            "X-Api-Key": this.apiKey,
          }
        : undefined,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `Delete session failed: ${response.status} - ${errorText}`
      );
    }

    return response.json();
  }

  /**
   * Load session history messages to checkpoint
   */
  async loadSession(
    sessionId: string,
    threadId?: string
  ): Promise<LoadSessionResponse> {
    const url = new URL(`${this.baseUrl}/api/session/${sessionId}/load`);
    if (threadId) {
      url.searchParams.append("thread_id", threadId);
    }

    const response = await fetch(url.toString(), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(this.apiKey && {
          "X-Api-Key": this.apiKey,
        }),
      },
      body: JSON.stringify({ thread_id: threadId }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `Load session failed: ${response.status} - ${errorText}`
      );
    }

    return response.json();
  }

  /**
   * Get session history messages
   */
  async getSessionMessages(
    sessionId: string,
    threadId?: string,
    limit: number = 50
  ): Promise<any[]> {
    const url = new URL(`${this.baseUrl}/api/session/${sessionId}/messages`);
    if (threadId) {
      url.searchParams.append("thread_id", threadId);
    }
    if (limit) {
      url.searchParams.append("limit", limit.toString());
    }

    const response = await fetch(url.toString(), {
      headers: this.apiKey
        ? {
            "X-Api-Key": this.apiKey,
          }
        : undefined,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `Get session messages failed: ${response.status} - ${errorText}`
      );
    }

    const data = await response.json();
    return data.messages;
  }

  /**
   * Get all sessions list
   */
  async getSessions(): Promise<SessionInfo[]> {
    const response = await fetch(`${this.baseUrl}/api/sessions`, {
      headers: this.apiKey
        ? {
            "X-Api-Key": this.apiKey,
          }
        : undefined,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `Get sessions failed: ${response.status} - ${errorText}`
      );
    }

    const data: SessionsResponse = await response.json();
    return data.sessions;
  }

  /**
   * Create new session
   */
  async createSession(title?: string): Promise<SessionInfo> {
    const url = new URL(`${this.baseUrl}/api/session`);
    if (title) {
      url.searchParams.append("title", title);
    }

    const response = await fetch(url.toString(), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(this.apiKey && {
          "X-Api-Key": this.apiKey,
        }),
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `Create session failed: ${response.status} - ${errorText}`
      );
    }

    return response.json();
  }

  /**
   * Get session status
   */
  async getStatus(threadId: string): Promise<StatusResponse> {
    const response = await fetch(`${this.baseUrl}/api/status/${threadId}`, {
      headers: this.apiKey
        ? {
            "X-Api-Key": this.apiKey,
          }
        : undefined,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `Get status failed: ${response.status} - ${errorText}`
      );
    }

    return response.json();
  }

  /**
   * Health check
   */
  async health(): Promise<HealthResponse> {
    const response = await fetch(`${this.baseUrl}/api/health`, {
      headers: this.apiKey
        ? {
            "X-Api-Key": this.apiKey,
          }
        : undefined,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `Health check failed: ${response.status} - ${errorText}`
      );
    }

    return response.json();
  }

  /**
   * Get configuration
   */
  async getConfig(): Promise<ConfigGetResponse> {
    const response = await fetch(`${this.baseUrl}/api/config`, {
      headers: this.apiKey
        ? {
            "X-Api-Key": this.apiKey,
          }
        : undefined,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `Get config failed: ${response.status} - ${errorText}`
      );
    }

    return response.json();
  }

  /**
   * Update configuration
   */
  async updateConfig(
    config: ConfigUpdateRequest
  ): Promise<ConfigUpdateResponse> {
    const response = await fetch(`${this.baseUrl}/api/config`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(this.apiKey && {
          "X-Api-Key": this.apiKey,
        }),
      },
      body: JSON.stringify(config),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `Update config failed: ${response.status} - ${errorText}`
      );
    }

    return response.json();
  }
}
