/**
 * API Adapter Layer - For converting between backend custom API format and LangGraph SDK format
 */

import { v4 as uuidv4 } from "uuid";
import { Interrupt } from "@langchain/langgraph-sdk";
import { HITLRequest, ActionRequest, ReviewConfig } from "@/components/thread/agent-inbox/types";

/**
 * Backend interrupt response format (matches interrupt_info in backend ChatResponse)
 */
export interface BackendInterrupt {
  todo_list: {
    id: string;
    description: string;
    tool: string;
  }[];
  tool_list: {
    name: string;
    description: string;
  }[];
}

/**
 * Backend chat response format (matches backend ChatResponse)
 */
export interface BackendChatResponse {
  status: "completed" | "interrupted" | "pending_confirmation";
  thread_id: string;
  todo_list?: {
    id: string;
    description: string;
    tool: string;
  }[];
  tool_list?: {
    name: string;
    description: string;
  }[];
  result?: {
    execution_results?: any;
    todo_list?: any[];
    tool_list?: any[];
  };
  interrupt_info?: BackendInterrupt;
  error_message?: string;
}

/**
 * Convert backend interrupt format to LangGraph SDK format
 *
 * Backend format:
 * {
 *   todo_list: [{id, description, tool}],
 *   tool_list: [{name, description}]
 * }
 *
 * SDK format:
 * {
 *   id: string,
 *   value: {
 *     action_requests: [{name, args, description}],
 *     review_configs: [{action_name, allowed_decisions}]
 *   }
 * }
 */
export function convertInterruptToSDKFormat(
  backendInterrupt: BackendInterrupt
): Interrupt<HITLRequest> {
  // Convert todo_list to action_requests
  const actionRequests: ActionRequest[] = backendInterrupt.todo_list.map((todo) => ({
    name: "execute_task",
    args: {
      task_id: todo.id,
      description: todo.description,
      tool: todo.tool,
    },
    description: `Execute task: ${todo.description}`,
  }));

  // Create review_config
  const reviewConfigs: ReviewConfig[] = [
    {
      action_name: "execute_task",
      allowed_decisions: ["approve", "reject"],
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
 * Convert user decision back to backend format
 *
 * SDK decision format:
 * { type: 'approve' | 'reject', message?: string }
 *
 * Backend format:
 * { thread_id: string, action: 'approve' | 'reject', reason?: string }
 */
export function convertDecisionToBackendFormat(
  decision: { type: "approve" | "reject"; message?: string },
  threadId: string
): { thread_id: string; action: string; reason?: string } {
  return {
    thread_id: threadId,
    action: decision.type === "approve" ? "approve" : "reject",
    reason: decision.type === "reject" ? decision.message : undefined,
  };
}

/**
 * Convert SDK interrupt array to backend format (for display)
 */
export function convertSDKInterruptsToBackendFormat(
  interrupts: Interrupt<HITLRequest>[] | Interrupt<HITLRequest>
): BackendInterrupt | null {
  const interruptArray = Array.isArray(interrupts) ? interrupts : [interrupts];

  if (interruptArray.length === 0) {
    return null;
  }

  const firstInterrupt = interruptArray[0];
  if (!firstInterrupt?.value?.action_requests) {
    return null;
  }

  const hitlValue = firstInterrupt.value as HITLRequest;

  // Convert action_requests back to todo_list
  const todoList = hitlValue.action_requests.map((request) => ({
    id: request.args.task_id as string || uuidv4(),
    description: request.description || (request.args.description as string) || "",
    tool: (request.args.tool as string) || "unknown",
  }));

  // Create tool_list (extracted from action_requests)
  const toolList = Array.from(
    new Set(hitlValue.action_requests.map((r) => r.args.tool as string).filter(Boolean))
  ).map((toolName) => ({
    name: toolName,
    description: `Execute ${toolName} task`,
  }));

  return {
    todo_list: todoList,
    tool_list: toolList,
  };
}
