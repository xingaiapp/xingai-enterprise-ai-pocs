export const API_BASE_URL =
  process.env.CLAIMS_API_BASE_URL ?? "https://api.claims.example.com/v1";

export const API_TIMEOUT_MS = Number(process.env.CLAIMS_API_TIMEOUT_MS ?? 30000);

// Caps how much text a single tool call can return so a large claims list
// or note history doesn't blow out the agent's context window.
export const CHARACTER_LIMIT = 25000;

export const DEFAULT_PAGE_SIZE = 25;
export const MAX_PAGE_SIZE = 100;

export enum ResponseFormat {
  MARKDOWN = "markdown",
  JSON = "json",
}
