/**
 * Session Provider - Wrapper for useSession Hook
 */

"use client";

import { createContext, useContext, ReactNode } from "react";
import { useSession, UseSessionReturn } from "../hooks/useSession";

const SessionContext = createContext<UseSessionReturn | undefined>(undefined);

export function SessionProvider({ children }: { children: ReactNode }) {
  const session = useSession();
  return <SessionContext.Provider value={session}>{children}</SessionContext.Provider>;
}

export function useSessionContext(): UseSessionReturn {
  const context = useContext(SessionContext);
  if (context === undefined) {
    throw new Error("useSessionContext must be used within a SessionProvider");
  }
  return context;
}
