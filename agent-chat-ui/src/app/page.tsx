"use client";

import { Thread } from "@/components/thread";
import { ChatProvider } from "@/providers/Chat";
import { SessionProvider } from "@/providers/Session";
import { ArtifactProvider } from "@/components/thread/artifact";
import { Toaster } from "@/components/ui/sonner";
import React from "react";

export default function DemoPage(): React.ReactNode {
  return (
    <React.Suspense fallback={<div>Loading (layout)...</div>}>
      <Toaster />
      <SessionProvider>
        <ChatProvider>
          <ArtifactProvider>
            <Thread />
          </ArtifactProvider>
        </ChatProvider>
      </SessionProvider>
    </React.Suspense>
  );
}
