import { randomUUID } from "node:crypto";
import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { claimsApiRequest, formatToolError } from "../services/api-client.js";
import { renderText, humanDate, money } from "../services/format.js";
import { claimIdField, responseFormatField } from "../schemas/common.js";
import type { Payment } from "../types.js";

function paymentToMarkdown(p: Payment): string {
  return [
    `## Payment ${p.paymentId} — ${money(p.amount, p.currency)} (${p.status})`,
    `- **Claim**: ${p.claimId}`,
    `- **Method**: ${p.method}`,
    `- **Payee**: ${p.payeeName}`,
    `- **Created**: ${humanDate(p.createdAt)}`,
    ...(p.issuedAt ? [`- **Issued**: ${humanDate(p.issuedAt)}`] : []),
  ].join("\n");
}

export function registerPaymentTools(server: McpServer): void {
  // --- claims_list_payments -------------------------------------------------
  const ListPaymentsSchema = z
    .object({
      claimId: claimIdField,
      response_format: responseFormatField,
    })
    .strict();

  server.registerTool(
    "claims_list_payments",
    {
      title: "List Claim Payments",
      description: `List payments/settlements issued for a claim.

This is a READ-ONLY operation.

Args:
  - claimId (string, required)

Returns: an array of Payment objects (amount, method, status, timestamps).`,
      inputSchema: ListPaymentsSchema.shape,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    async ({ claimId, response_format }) => {
      try {
        const payments = await claimsApiRequest<Payment[]>(
          `/claims/${encodeURIComponent(claimId)}/payments`
        );
        const structured = { claimId, payments };
        const { text } = renderText(response_format, structured, () => {
          if (!payments.length) return `No payments recorded for ${claimId}.`;
          return [`# Payments — ${claimId}`, "", ...payments.map(paymentToMarkdown)].join("\n\n");
        });
        return { content: [{ type: "text", text }], structuredContent: structured };
      } catch (error) {
        return { isError: true, content: [{ type: "text", text: formatToolError(error) }] };
      }
    }
  );

  // --- claims_create_payment -------------------------------------------------
  const CreatePaymentSchema = z
    .object({
      claimId: claimIdField,
      amount: z.number().min(0.01).describe("Settlement amount to pay out"),
      currency: z.string().length(3).default("USD").describe("ISO 4217 currency code"),
      method: z.enum(["ach", "check", "wire", "card"]).describe("Disbursement method"),
      payeeName: z.string().min(1).describe("Name of the payee (usually the claimant)"),
      idempotencyKey: z
        .string()
        .optional()
        .describe(
          "Idempotency key so a network retry can't double-pay; if omitted, a random key is generated for this single call"
        ),
      response_format: responseFormatField,
    })
    .strict();

  server.registerTool(
    "claims_create_payment",
    {
      title: "Issue Claim Settlement Payment",
      description: `Issue a settlement payment for a claim that is already in status 'approved'.

This is a WRITE, DESTRUCTIVE-CLASS operation (moves real money). The
underlying API requires an Idempotency-Key so retries are safe; if you
don't supply idempotencyKey, one is generated for this call only — reuse the
same key yourself if you need to safely retry after a timeout.

Args:
  - claimId, amount, method ('ach'|'check'|'wire'|'card'), payeeName (all required)
  - currency (default 'USD')
  - idempotencyKey (optional)

Returns: the created Payment object. The claim moves to status 'in_payment' on success.

Error handling:
  - Returns a conflict error if the claim is not currently 'approved'.
  - Returns a conflict error if idempotencyKey was already used with a different payload.`,
      inputSchema: CreatePaymentSchema.shape,
      annotations: {
        readOnlyHint: false,
        destructiveHint: true,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    async ({ claimId, response_format, idempotencyKey, ...body }) => {
      try {
        const key = idempotencyKey ?? randomUUID();
        const payment = await claimsApiRequest<Payment>(
          `/claims/${encodeURIComponent(claimId)}/payments`,
          "POST",
          { ...body, idempotencyKey: key },
          { headers: { "Idempotency-Key": key } }
        );
        const { text } = renderText(response_format, payment, () => paymentToMarkdown(payment));
        return { content: [{ type: "text", text }], structuredContent: payment };
      } catch (error) {
        return { isError: true, content: [{ type: "text", text: formatToolError(error) }] };
      }
    }
  );

  // --- claims_get_payment -------------------------------------------------
  const GetPaymentSchema = z
    .object({
      paymentId: z.string().min(1).describe("Payment ID"),
      response_format: responseFormatField,
    })
    .strict();

  server.registerTool(
    "claims_get_payment",
    {
      title: "Get Payment Status",
      description: `Fetch a single payment's status by ID.

This is a READ-ONLY operation.

Args:
  - paymentId (string, required)

Returns: the Payment object, including current status ('pending'|'issued'|'failed'|'cancelled').`,
      inputSchema: GetPaymentSchema.shape,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    async ({ paymentId, response_format }) => {
      try {
        const payment = await claimsApiRequest<Payment>(`/payments/${encodeURIComponent(paymentId)}`);
        const { text } = renderText(response_format, payment, () => paymentToMarkdown(payment));
        return { content: [{ type: "text", text }], structuredContent: payment };
      } catch (error) {
        return { isError: true, content: [{ type: "text", text: formatToolError(error) }] };
      }
    }
  );
}
