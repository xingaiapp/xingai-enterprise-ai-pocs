import { CHARACTER_LIMIT, ResponseFormat } from "../constants.js";

/**
 * Shared formatting helpers so every tool renders JSON vs. Markdown, and
 * truncates oversized responses, the same way instead of re-implementing it
 * per tool.
 */

export function renderText(
  format: ResponseFormat,
  structured: unknown,
  toMarkdown: () => string
): { text: string; truncated: boolean } {
  let text =
    format === ResponseFormat.JSON
      ? JSON.stringify(structured, null, 2)
      : toMarkdown();

  let truncated = false;
  if (text.length > CHARACTER_LIMIT) {
    truncated = true;
    text =
      text.slice(0, CHARACTER_LIMIT) +
      `\n\n[...truncated: response exceeded ${CHARACTER_LIMIT} characters. Narrow your filters, reduce pageSize, or request response_format="json" for a more compact payload.]`;
  }
  return { text, truncated };
}

export function humanDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().replace("T", " ").replace("Z", " UTC");
}

export function money(amount: number | null | undefined, currency = "USD"): string {
  if (amount === null || amount === undefined) return "—";
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(amount);
}
