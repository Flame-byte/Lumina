import { useEffect, useRef, useState } from "react";
import { useChatContext } from "@/providers/Chat";
import {
  Decision,
  DecisionWithEdits,
  SubmitType,
  ActionRequest,
  ReviewConfig,
} from "../types";
import { toast } from "sonner";

interface UseInterruptedActionsInput {
  interrupt: {
    value: {
      action_requests: ActionRequest[];
      review_configs: ReviewConfig[];
    };
  };
}

interface UseInterruptedActionsValue {
  handleSubmit: (
    e: React.MouseEvent<HTMLButtonElement, MouseEvent> | KeyboardEvent,
  ) => Promise<void>;
  handleResolve: (
    e: React.MouseEvent<HTMLButtonElement, MouseEvent>,
  ) => Promise<void>;
  streaming: boolean;
  streamFinished: boolean;
  loading: boolean;
  supportsMultipleMethods: boolean;
  hasEdited: boolean;
  hasAddedResponse: boolean;
  approveAllowed: boolean;
  humanResponse: DecisionWithEdits[];
  selectedSubmitType: SubmitType | undefined;
  setSelectedSubmitType: (value: SubmitType | undefined) => void;
  setHumanResponse: (value: DecisionWithEdits[] | ((prev: DecisionWithEdits[]) => DecisionWithEdits[])) => void;
  setHasAddedResponse: (value: boolean | ((prev: boolean) => boolean)) => void;
  setHasEdited: (value: boolean | ((prev: boolean) => boolean)) => void;
  initialHumanInterruptEditValue: React.MutableRefObject<Record<string, string>>;
}

export default function useInterruptedActions({
  interrupt,
}: UseInterruptedActionsInput): UseInterruptedActionsValue {
  const chat = useChatContext();
  const [humanResponse, setHumanResponse] = useState<DecisionWithEdits[]>([]);
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [streamFinished, setStreamFinished] = useState(false);
  const [selectedSubmitType, setSelectedSubmitType] = useState<SubmitType>();
  const [hasEdited, setHasEdited] = useState(false);
  const [hasAddedResponse, setHasAddedResponse] = useState(false);
  const [approveAllowed, setApproveAllowed] = useState(false);
  const initialHumanInterruptEditValue = useRef<Record<string, string>>({});

  useEffect(() => {
    const hitlValue = interrupt.value;
    initialHumanInterruptEditValue.current = {};

    if (!hitlValue) {
      setHumanResponse([]);
      setSelectedSubmitType(undefined);
      setApproveAllowed(false);
      setHasEdited(false);
      setHasAddedResponse(false);
      return;
    }

    // Simple initialization logic - determine allowed operations based on review_configs
    const reviewConfig = hitlValue.review_configs?.[0];
    const hasApprove = reviewConfig?.allowed_decisions?.includes("approve");

    // Set default response
    const responses: DecisionWithEdits[] = [];
    if (hasApprove) {
      responses.push({ type: "approve" });
    }
    responses.push({ type: "reject" });

    setHumanResponse(responses);
    setSelectedSubmitType(hasApprove ? "approve" : "reject");
    setApproveAllowed(hasApprove);
    setHasEdited(false);
    setHasAddedResponse(false);
  }, [interrupt]);

  const resumeRun = (decisions: Decision[]): boolean => {
    try {
      // Use custom confirm/reject methods
      const decision = decisions[0];
      if (decision.type === "approve") {
        chat.confirm();
      } else if (decision.type === "reject") {
        // Get feedback from humanResponse
        const rejectDecision = humanResponse.find(d => d.type === "reject");
        const feedback = rejectDecision?.message || "User rejected the plan";
        chat.reject(feedback);
      }
      return true;
    } catch (error) {
      console.error("Error sending human response", error);
      return false;
    }
  };

  const handleSubmit = async (
    e: React.MouseEvent<HTMLButtonElement, MouseEvent> | KeyboardEvent,
  ) => {
    e.preventDefault();

    // Get feedback from humanResponse (if reject)
    let decision: Decision;
    if (selectedSubmitType === "approve") {
      decision = { type: "approve" };
    } else {
      // For reject, get feedback from humanResponse
      const rejectDecision = humanResponse.find(d => d.type === "reject");
      const feedback = rejectDecision?.message || "User rejected the plan";
      decision = { type: "reject", message: feedback };
    }

    let errorOccurred = false;
    initialHumanInterruptEditValue.current = {};

    try {
      setLoading(true);
      setStreaming(true);

      const resumedSuccessfully = resumeRun([decision]);
      if (!resumedSuccessfully) {
        errorOccurred = true;
        return;
      }

      toast("Success", {
        description: "Response submitted successfully.",
        duration: 5000,
      });

      setStreamFinished(true);
    } catch (error: any) {
      console.error("Error sending human response", error);
      errorOccurred = true;

      toast.error("Error", {
        description: "Failed to submit response.",
        richColors: true,
        closeButton: true,
        duration: 5000,
      });
    } finally {
      setStreaming(false);
      setLoading(false);
      if (errorOccurred) {
        setStreamFinished(false);
      }
    }
  };

  const handleResolve = async (
    e: React.MouseEvent<HTMLButtonElement, MouseEvent>,
  ) => {
    e.preventDefault();
    setLoading(true);
    initialHumanInterruptEditValue.current = {};

    try {
      // For resolve operation, we don't execute anything, just clear the interrupt
      // This may require backend support for a new endpoint
      toast("Info", {
        description: "Resolve functionality may require backend support.",
        duration: 3000,
      });
    } catch (error) {
      console.error("Error marking thread as resolved", error);
      toast.error("Error", {
        description: "Failed to mark thread as resolved.",
        richColors: true,
        closeButton: true,
        duration: 3000,
      });
    } finally {
      setLoading(false);
    }
  };

  const supportsMultipleMethods =
    humanResponse.filter((response) =>
      ["edit", "approve", "reject"].includes(response.type),
    ).length > 1;

  return {
    handleSubmit,
    handleResolve,
    humanResponse,
    selectedSubmitType,
    streaming,
    streamFinished,
    loading,
    supportsMultipleMethods,
    hasEdited,
    hasAddedResponse,
    approveAllowed,
    setSelectedSubmitType,
    setHumanResponse,
    setHasAddedResponse,
    setHasEdited,
    initialHumanInterruptEditValue,
  };
}
