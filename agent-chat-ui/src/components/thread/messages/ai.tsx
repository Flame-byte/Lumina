import { useChatContext } from "@/providers/Chat";
import type { Message } from "@/hooks/useChat";
import type { TodoItem } from "@/types/api";
import { getContentString } from "../utils";
import { MarkdownText } from "../markdown-text";
import { ThreadView } from "../agent-inbox";
import { TodoListCard } from "./todo-list-card";

interface AssistantMessageProps {
  message: Message | undefined;
  isLoading: boolean;
  handleRegenerate: () => void;
}

export function AssistantMessage({
  message,
  isLoading,
  handleRegenerate,
}: AssistantMessageProps) {
  const content = message?.content ?? [];
  const contentString = getContentString(content);

  const chat = useChatContext();

  // If there is an interrupt, show HITL UI
  // Always show interrupt when it exists, regardless of existing AI messages (supports showing interrupts in multi-turn conversation)
  const interrupt = chat.interrupt;

  // Parse todo_list JSON
  const todoList = parseTodoListJson(contentString);

  return (
    <div className="group mr-auto flex w-full items-start gap-2">
      <div className="flex w-full flex-col gap-2">
        {/* If there is todo_list, show structured card; otherwise show Markdown text */}
        {todoList ? (
          <TodoListCard todoList={todoList} />
        ) : contentString.length > 0 ? (
          <div className="py-1">
            <MarkdownText>{contentString}</MarkdownText>
          </div>
        ) : null}

        {/* Show interrupt (HITL confirm interface) */}
        {interrupt && (
          <div className="mt-2 w-full">
            <ThreadView interrupt={interrupt} />
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Try to parse todo_list from content string
 * Only recognizes JSON objects containing todo_list array
 * @returns TodoItem[] if parsing succeeds, otherwise returns null
 */
function parseTodoListJson(content: string): TodoItem[] | null {
  if (!content || typeof content !== "string") {
    return null;
  }

  try {
    // Try to extract JSON part (handle possible markdown code block wrapping)
    let jsonStr = content.trim();

    // If it's markdown code block format, extract JSON part
    if (jsonStr.startsWith("```json")) {
      jsonStr = jsonStr.replace(/^```json\s*/, "").replace(/\s*```$/, "");
    } else if (jsonStr.startsWith("```")) {
      jsonStr = jsonStr.replace(/^```\s*/, "").replace(/\s*```$/, "");
    }

    const parsed = JSON.parse(jsonStr);

    // Only recognize objects containing todo_list array
    if (parsed && typeof parsed === "object" && Array.isArray(parsed.todo_list)) {
      // Validate array element format
      const isValid = parsed.todo_list.every(
        (item: unknown) =>
          item &&
          typeof item === "object" &&
          "id" in item &&
          "description" in item &&
          "tool" in item
      );

      if (isValid) {
        return parsed.todo_list as TodoItem[];
      }
    }

    return null;
  } catch {
    // Parsing failed, return null
    return null;
  }
}

export function AssistantMessageLoading() {
  return (
    <div className="mr-auto flex items-start gap-2">
      <div className="bg-muted flex h-8 items-center gap-1 rounded-2xl px-4 py-2">
        <div className="bg-foreground/50 h-1.5 w-1.5 animate-[pulse_1.5s_ease-in-out_infinite] rounded-full"></div>
        <div className="bg-foreground/50 h-1.5 w-1.5 animate-[pulse_1.5s_ease-in-out_0.5s_infinite] rounded-full"></div>
        <div className="bg-foreground/50 h-1.5 w-1.5 animate-[pulse_1.5s_ease-in-out_1s_infinite] rounded-full"></div>
      </div>
    </div>
  );
}
