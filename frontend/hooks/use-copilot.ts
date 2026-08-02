import { useState } from "react";
import { useApi } from "./use-api";

export interface ActionProposal {
  action_id: string;
  action_type: string;
  status: string;
  expires_at: string;
  payload: Record<string, unknown>;
  display_title: string;
  display_subtitle: string;
  display_quantity: string;
}

export interface Message {
  id: string;
  role: "user" | "copilot";
  content: string;
  actionProposals?: ActionProposal[];
}

export function useCopilot() {
  const { request } = useApi();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = async (content: string) => {
    if (!content.trim()) return;

    const userMessage: Message = { id: Date.now().toString(), role: "user", content };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      const response = await request("/api/v1/copilot/chat", {
        method: "POST",
        body: JSON.stringify({ message: content }),
      });

      const copilotMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "copilot",
        content: response.answer,
        actionProposals: response.action_proposals,
      };

      setMessages((prev) => [...prev, copilotMessage]);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Failed to communicate with Copilot.";
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const executeAction = async (actionId: string) => {
    return request(`/api/v1/copilot/actions/${actionId}/execute`, {
      method: "POST",
    });
  };

  const cancelAction = async (actionId: string) => {
    return request(`/api/v1/copilot/actions/${actionId}/cancel`, {
      method: "POST",
    });
  };

  const clearChat = () => {
    setMessages([]);
    setError(null);
  };

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    executeAction,
    cancelAction,
    clearChat,
  };
}
