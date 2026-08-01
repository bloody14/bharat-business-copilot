/**
 * Reusable fetch wrapper for authenticated API calls.
 */

export class ApiError extends Error {
  constructor(public status: number, message: string, public data?: unknown) {
    super(message);
    this.name = "ApiError";
  }
}

export async function fetchWithAuth(
  endpoint: string,
  token: string | null,
  options: RequestInit = {}
) {
  if (!token) {
    throw new Error("Cannot make authenticated request: No valid session token available.");
  }

  const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  // ensure endpoint starts with /
  const path = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  const url = `${baseUrl}${path}`;

  const headers = new Headers(options.headers);
  headers.set("Authorization", `Bearer ${token}`);
  if (!headers.has("Content-Type") && options.body && typeof options.body === "string") {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorData;
    try {
      errorData = await response.json();
    } catch {
      errorData = { detail: response.statusText };
    }
    // FastAPI validation errors are usually in `detail` array
    let message = `Request failed with status ${response.status}`;
    if (typeof errorData?.detail === "string") {
      message = errorData.detail;
    } else if (Array.isArray(errorData?.detail) && errorData.detail.length > 0) {
      message = errorData.detail[0].msg || message;
    }
    
    throw new ApiError(response.status, message, errorData);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}
