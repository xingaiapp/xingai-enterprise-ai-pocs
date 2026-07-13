import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { claimsApiRequest, formatToolError } from "../services/api-client.js";
import { renderText, humanDate } from "../services/format.js";
import { claimIdField, responseFormatField } from "../schemas/common.js";
import type { Claim, StatusEvent } from "../types.js";
import { claimToMarkdown } from "./claims.js";

const ClaimStatusEnum = z.enum([
  "submitted",
  "under_review",
  "approved",
  "denied",
  "in_payment",
  "closed",
  "reopened",
]);

export function registerStatusTools(server: McpServer): void {
  // --- claims_transition_status ------------------------------------------
  const TransitionSchema = z
    .object({
      claimId: claimIdField,
      toStatus: ClaimStatusEnum.describe("Target status for the claim"),
      reason: z.string().optional().describe("Reason for the transition; required when denying a claim"),
      approvedAmount: z
        .number()
        .min(0)
        .optional()
        .describe("Required when toStatus='approved' — the amount approved for settlement"),
      response_format: responseFormatField,
    })
    .strict();

  server.registerTool(
    "claims_transition_status",
    {
      title: "Transition Claim Status",
      description: `Move a claim to a new status in its lifecycle (e.g. submit for review, approve, deny, close, reopen).

This is a WRITE operation with real business effect — approving or denying a
claim is a binding adjudication decision. Only transitions legal from the
claim's current status are accepted; illegal transitions return a conflict
error naming the current status.

Args:
  - claimId (string, required)
  - toStatus ('submitted'|'under_review'|'approved'|'denied'|'in_payment'|'closed'|'reopened', required)
  - reason (string, optional but required when toStatus='denied')
  - approvedAmount (number, required when toStatus='approved')

Returns: the updated Claim object reflecting the new status.

Error handling:
  - Returns a conflict error if the transition is not legal from the current status.
  - Use claims_list_status_history to see the claim's full transition trail first if unsure what's legal next.`,
      inputSchema: TransitionSchema.shape,
      annotations: {
        readOnlyHint: false,
        destructiveHint: true,
        idempotentHint: false,
        openWorldHint: true,
      },
    },
    async ({ claimId, response_format, ...body }) => {
      try {
        const claim = await claimsApiRequest<Claim>(
          `/claims/${encodeURIComponent(claimId)}/status`,
          "POST",
          body
        );
        const { text } = renderText(response_format, claim, () => claimToMarkdown(claim));
        return { content: [{ type: "text", text }], structuredContent: claim };
      } catch (error) {
        return { isError: true, content: [{ type: "text", text: formatToolError(error) }] };
      }
    }
  );

  // --- claims_list_status_history -----------------------------------------
  const HistorySchema = z
    .object({
      claimId: claimIdField,
      response_format: responseFormatField,
    })
    .strict();

  server.registerTool(
    "claims_list_status_history",
    {
      title: "List Claim Status History",
      description: `List the full ordered history of status transitions for a claim (oldest first).

This is a READ-ONLY operation.

Args:
  - claimId (string, required)

Returns: an array of StatusEvent objects (fromStatus, toStatus, reason, actorId, occurredAt).

Examples:
  - "Why was this claim denied?" -> look at the last event's reason field.`,
      inputSchema: HistorySchema.shape,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    async ({ claimId, response_format }) => {
      try {
        const events = await claimsApiRequest<StatusEvent[]>(
          `/claims/${encodeURIComponent(claimId)}/status-history`
        );
        const structured = { claimId, events };
        const { text } = renderText(response_format, structured, () => {
          if (!events.length) return `No status history recorded for ${claimId}.`;
          const lines = [`# Status History — ${claimId}`, ""];
          for (const e of events) {
            lines.push(
              `- ${humanDate(e.occurredAt)}: **${e.fromStatus} → ${e.toStatus}**` +
                (e.reason ? ` — ${e.reason}` : "") +
                ` (by ${e.actorId})`
            );
          }
          return lines.join("\n");
        });
        return { content: [{ type: "text", text }], structuredContent: structured };
      } catch (error) {
        return { isError: true, content: [{ type: "text", text: formatToolError(error) }] };
      }
    }
  );
}
