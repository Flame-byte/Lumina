/**
 * Chat Provider - Wrapper for useChat Hook
 */

"use client";

import { createContext, useContext, ReactNode } from "react";
import { useChat, UseChatReturn } from "../hooks/useChat";

const ChatContext = createContext<UseChatReturn | undefined>(undefined);

export function ChatProvider({ children }: { children: ReactNode }) {
  const chat = useChat();
  return <ChatContext.Provider value={chat}>{children}</ChatContext.Provider>;
}

export function useChatContext(): UseChatReturn {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error("useChatContext must be used within a ChatProvider");
  }
  return context;
}
