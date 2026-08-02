import { useState } from "react";
import { useApi } from "./use-api";

export interface Message {
  id: string;
  role: "user" | "copilot";
  content: string;
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
      };

      setMessages((prev) => [...prev, copilotMessage]);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Failed to communicate with Copilot.";
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
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
    clearChat,
  };
}
