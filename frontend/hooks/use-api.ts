import { useAuth } from "@clerk/nextjs";
import { useCallback } from "react";
import { fetchWithAuth } from "@/lib/api-client";

export function useApi() {
  const { getToken, orgId } = useAuth();

  const request = useCallback(
    async (endpoint: string, options: RequestInit = {}) => {
      // The user must have an active organization to call business APIs
      if (!orgId) {
        throw new Error("No active organization. Please select an organization first.");
      }
      
      const token = await getToken();
      return fetchWithAuth(endpoint, token, options);
    },
    [getToken, orgId]
  );

  return { request };
}
