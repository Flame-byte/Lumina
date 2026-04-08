import { Button } from "@/components/ui/button";
import { useSessionContext } from "@/providers/Session";
import { useChatContext } from "@/providers/Chat";
import type { SessionInfo } from "@/types/api";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

import { useQueryState, parseAsBoolean } from "nuqs";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { PanelRightOpen, PanelRightClose, Plus, Trash2 } from "lucide-react";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function SessionList({
  sessions,
  onSessionClick,
  onDeleteSession,
}: {
  sessions: SessionInfo[];
  onSessionClick?: (sessionId: string) => void;
  onDeleteSession?: (sessionId: string, e: React.MouseEvent) => void;
}) {
  const [sessionId, _setSessionId] = useQueryState("sessionId");
  const { switchSession } = useSessionContext();
  const { setMessages } = useChatContext();

  const handleClick = async (id: string) => {
    if (id === sessionId) return;
    try {
      onSessionClick?.(id);

      // Switch session and get history messages
      const messages = await switchSession(id);

      // Reset chat messages to new session's history messages
      setMessages(messages);

      toast.success("Session switched");
    } catch (error) {
      toast.error("Failed to switch session", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    }
  };

  // Empty state prompt
  if (sessions.length === 0) {
    return (
      <div className="flex h-full w-full flex-col items-center justify-center gap-2 p-4 text-center">
        <p className="text-sm text-gray-500">No session history</p>
        <p className="text-xs text-gray-400">Click "New Session" to start</p>
      </div>
    );
  }

  return (
    <div className="flex h-full w-full flex-col items-start justify-start gap-2 overflow-y-scroll [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300 [&::-webkit-scrollbar-track]:bg-transparent">
      {sessions.map((s) => {
        const itemText = s.title || s.id;
        const isSelected = s.id === sessionId;
        return (
          <div
            key={s.id}
            className={cn(
              "group flex w-full items-center justify-between gap-1 px-1",
              isSelected && "rounded-md bg-gray-200",
            )}
          >
            <Button
              variant="ghost"
              className={cn(
                "flex-1 items-start justify-start text-left font-normal",
                isSelected && "bg-transparent hover:bg-gray-300",
              )}
              onClick={() => handleClick(s.id)}
            >
              <p className="truncate text-ellipsis">{itemText}</p>
            </Button>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
                  onClick={(e) => e.stopPropagation()}
                >
                  <Trash2 className="h-4 w-4 text-red-500" />
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Delete Session</AlertDialogTitle>
                  <AlertDialogDescription>
                    Are you sure you want to delete session "{itemText}"? This action cannot be undone.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteSession?.(s.id, e as any);
                    }}
                  >
                    Delete
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        );
      })}
    </div>
  );
}

function SessionHistoryLoading() {
  return (
    <div className="flex h-full w-full flex-col items-start justify-start gap-2 overflow-y-scroll [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300 [&::-webkit-scrollbar-track]:bg-transparent">
      {Array.from({ length: 30 }).map((_, i) => (
        <Skeleton
          key={`skeleton-${i}`}
          className="h-10 w-[280px]"
        />
      ))}
    </div>
  );
}

export default function ThreadHistory() {
  const isLargeScreen = useMediaQuery("(min-width: 1024px)");
  const [chatHistoryOpen, setChatHistoryOpen] = useQueryState(
    "chatHistoryOpen",
    parseAsBoolean.withDefault(true),
  );
  const [sessionId, _setSessionId] = useQueryState("sessionId");
  const [threadId, _setThreadId] = useQueryState("threadId");

  const { sessions, sessionsLoading, loadSessions, deleteSession, createSession } = useSessionContext();
  const { setMessages } = useChatContext();
  const [isCreating, setIsCreating] = useState(false);
  const [isNewSessionDialogOpen, setIsNewSessionDialogOpen] = useState(false);
  const [newSessionName, setNewSessionName] = useState("");

  // Load session list on initialization
  useEffect(() => {
    if (typeof window === "undefined") return;
    loadSessions();
  }, [loadSessions]);

  // Click new session button, open dialog
  const handleOpenNewSessionDialog = async () => {
    // Calculate default name: New Session n (n = current session count + 1)
    const nextSessionNumber = sessions.length + 1;
    setNewSessionName(`New Session ${nextSessionNumber}`);
    setIsNewSessionDialogOpen(true);
  };

  // Confirm create session
  const handleCreateSession = async () => {
    try {
      setIsCreating(true);
      // Create new session with user-provided title
      const newSessionId = await createSession(newSessionName);

      // Reset chat messages
      setMessages([]);

      // Update URL params
      _setSessionId(newSessionId);
      _setThreadId(null);

      toast.success("New session created");

      // Refresh session list
      await loadSessions();

      // Close dialog
      setIsNewSessionDialogOpen(false);
    } catch (error) {
      toast.error("Failed to create session", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setIsCreating(false);
    }
  };

  // Delete session
  const handleDeleteSession = async (sessionIdToDelete: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await deleteSession(sessionIdToDelete);
      toast.success("Session deleted");

      // Refresh list
      await loadSessions();
    } catch (error) {
      toast.error("Failed to delete session", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    }
  };

  return (
    <>
      <div className="shadow-inner-right hidden h-screen w-[300px] shrink-0 flex-col items-start justify-start gap-6 border-r-[1px] border-slate-300 lg:flex">
        {/* Header area - only show toggle button and title */}
        <div className="flex w-full flex-col gap-2 px-4 pt-1.5">
          <div className="flex w-full items-center justify-between">
            <Button
              className="hover:bg-gray-100"
              variant="ghost"
              onClick={() => setChatHistoryOpen((p) => !p)}
            >
              {chatHistoryOpen ? (
                <PanelRightOpen className="size-5" />
              ) : (
                <PanelRightClose className="size-5" />
              )}
            </Button>
            <h1 className="text-xl font-semibold tracking-tight">
              Session History
            </h1>
          </div>
        </div>

        {/* Session list - occupies all middle space */}
        <div className="flex flex-1 overflow-hidden">
          {sessionsLoading ? (
            <SessionHistoryLoading />
          ) : (
            <SessionList
              sessions={sessions}
              onDeleteSession={handleDeleteSession}
            />
          )}
        </div>

        {/* Bottom new session button */}
        <div className="w-full border-t p-4">
          <Button
            variant="outline"
            className="w-full justify-start gap-2 bg-white hover:bg-gray-50"
            onClick={handleOpenNewSessionDialog}
            disabled={isCreating}
          >
            <Plus className="h-4 w-4" />
            New Session
          </Button>
        </div>
      </div>

      {/* Mobile sidebar */}
      <div className="lg:hidden">
        <Sheet
          open={!!chatHistoryOpen && !isLargeScreen}
          onOpenChange={(open) => {
            if (isLargeScreen) return;
            setChatHistoryOpen(open);
          }}
        >
          <SheetContent
            side="left"
            className="flex lg:hidden"
          >
            <SheetHeader>
              <SheetTitle>Session History</SheetTitle>
            </SheetHeader>
            <div className="mt-4 flex flex-1 flex-col overflow-hidden">
              {sessionsLoading ? (
                <SessionHistoryLoading />
              ) : (
                <SessionList
                  sessions={sessions}
                  onDeleteSession={handleDeleteSession}
                />
              )}
              <div className="mt-4 border-t pt-4">
                <Button
                  variant="outline"
                  className="w-full justify-start gap-2 bg-white hover:bg-gray-50"
                  onClick={handleOpenNewSessionDialog}
                  disabled={isCreating}
                >
                  <Plus className="h-4 w-4" />
                  New Session
                </Button>
              </div>
            </div>
          </SheetContent>
        </Sheet>
      </div>

      {/* New session name dialog */}
      <Dialog open={isNewSessionDialogOpen} onOpenChange={setIsNewSessionDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Session</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="session-name">Session Name</Label>
              <Input
                id="session-name"
                value={newSessionName}
                onChange={(e) => setNewSessionName(e.target.value)}
                placeholder="Enter session name"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    handleCreateSession();
                  }
                }}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsNewSessionDialogOpen(false)}
              disabled={isCreating}
            >
              Cancel
            </Button>
            <Button
              onClick={handleCreateSession}
              disabled={isCreating || !newSessionName.trim()}
            >
              {isCreating ? "Creating..." : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
