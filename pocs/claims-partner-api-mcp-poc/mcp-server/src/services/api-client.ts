import axios, { AxiosError, type Method } from "axios";
import { API_BASE_URL, API_TIMEOUT_MS } from "../constants.js";

/**
 * Thin, typed wrapper around the Claims Business API (see
 * ../../claims-api-openapi.yaml for the full contract). Centralizes auth,
 * timeouts, and error shaping so every tool gets consistent behavior.
 */

export class ClaimsApiError extends Error {
  readonly status?: number;
  readonly detail?: string;

  constructor(message: string, status?: number, detail?: string) {
    super(message);
    this.name = "ClaimsApiError";
    this.status = status;
    this.detail = detail;
  }
}

function getAuthToken(): string {
  const token = process.env.CLAIMS_API_TOKEN;
  if (!token) {
    throw new ClaimsApiError(
      "CLAIMS_API_TOKEN environment variable is not set. Configure an OAuth2 " +
        "client-credentials access token before calling the Claims API."
    );
  }
  return token;
}

export interface RequestOptions {
  params?: Record<string, string | number | boolean | undefined>;
  headers?: Record<string, string>;
}

export async function claimsApiRequest<T>(
  endpoint: string,
  method: Method = "GET",
  body?: unknown,
  options: RequestOptions = {}
): Promise<T> {
  try {
    const response = await axios({
      method,
      url: `${API_BASE_URL}${endpoint}`,
      data: body,
      params: options.params,
      timeout: API_TIMEOUT_MS,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        Authorization: `Bearer ${getAuthToken()}`,
        ...options.headers,
      },
    });
    return response.data as T;
  } catch (error) {
    throw toClaimsApiError(error);
  }
}

function toClaimsApiError(error: unknown): ClaimsApiError {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: string; message?: string }>;
    const status = axiosError.response?.status;
    const detail =
      axiosError.response?.data?.detail ?? axiosError.response?.data?.message;

    if (status === 401) {
      return new ClaimsApiError(
        "Authentication failed: the CLAIMS_API_TOKEN is missing, expired, or invalid.",
        401,
        detail
      );
    }
    if (status === 403) {
      return new ClaimsApiError(
        "Permission denied: the token does not have the OAuth scope required for this operation.",
        403,
        detail
      );
    }
    if (status === 404) {
      return new ClaimsApiError(
        "Not found: double-check the claim/policy/claimant/document/payment ID.",
        404,
        detail
      );
    }
    if (status === 409) {
      return new ClaimsApiError(
        `Conflict: ${detail ?? "the requested state change is not allowed from the resource's current state."}`,
        409,
        detail
      );
    }
    if (status === 429) {
      return new ClaimsApiError(
        "Rate limit exceeded: wait before retrying.",
        429,
        detail
      );
    }
    if (axiosError.code === "ECONNABORTED") {
      return new ClaimsApiError("Request timed out contacting the Claims API.");
    }
    return new ClaimsApiError(
      `Claims API request failed${status ? ` with status ${status}` : ""}${
        detail ? `: ${detail}` : ""
      }`,
      status,
      detail
    );
  }
  return new ClaimsApiError(
    `Unexpected error calling the Claims API: ${
      error instanceof Error ? error.message : String(error)
    }`
  );
}

/** Formats a ClaimsApiError (or any thrown error) into a tool-facing message. */
export function formatToolError(error: unknown): string {
  if (error instanceof ClaimsApiError) {
    return `Error: ${error.message}`;
  }
  if (error instanceof Error) {
    return `Error: ${error.message}`;
  }
  return `Error: ${String(error)}`;
}
