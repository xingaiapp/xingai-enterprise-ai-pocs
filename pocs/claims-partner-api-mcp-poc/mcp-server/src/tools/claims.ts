import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { claimsApiRequest, formatToolError } from "../services/api-client.js";
import { renderText, humanDate, money } from "../services/format.js";
import { claimIdField, paginationFields, responseFormatField } from "../schemas/common.js";
import { ResponseFormat } from "../constants.js";
import type { Claim, PaginatedResponse } from "../types.js";

const ClaimStatusEnum = z.enum([
  "submitted",
  "under_review",
  "approved",
  "denied",
  "in_payment",
  "closed",
  "reopened",
]);

function claimToMarkdown(c: Claim): string {
  return [
    `## ${c.claimId} — ${c.claimType} (${c.status})`,
    `- **Policy**: ${c.policyNumber}`,
    `- **Claimant**: ${c.claimantId}`,
    `- **Filed**: ${money(c.filedAmount, c.currency)} on ${humanDate(c.createdAt)}`,
    ...(c.approvedAmount != null ? [`- **Approved**: ${money(c.approvedAmount, c.currency)}`] : []),
    ...(c.adjusterId ? [`- **Adjuster**: ${c.adjusterId}`] : []),
    ...(c.tags.length ? [`- **Tags**: ${c.tags.join(", ")}`] : []),
    `- **Description**: ${c.description}`,
    `- **Updated**: ${humanDate(c.updatedAt)}`,
  ].join("\n");
}

export function registerClaimsTools(server: McpServer): void {
  // --- claims_list_claims ---------------------------------------------
  const ListClaimsSchema = z
    .object({
      status: ClaimStatusEnum.optional().describe("Filter by claim status"),
      policyNumber: z.string().optional().describe("Filter by policy number, e.g. 'POL-1001'"),
      claimantId: z.string().optional().describe("Filter by claimant ID"),
      filedAfter: z.string().optional().describe("ISO 8601 date-time; only claims filed at/after this instant"),
      filedBefore: z.string().optional().describe("ISO 8601 date-time; only claims filed before this instant"),
      ...paginationFields,
      response_format: responseFormatField,
    })
    .strict();

  server.registerTool(
    "claims_list_claims",
    {
      title: "List Claims",
      description: `List claims filed against the claims business, with optional filters.

This is a READ-ONLY operation. It does not create, modify, or resolve any claim.

Args:
  - status ('submitted'|'under_review'|'approved'|'denied'|'in_payment'|'closed'|'reopened', optional): filter by status
  - policyNumber (string, optional): filter by policy number
  - claimantId (string, optional): filter by claimant ID
  - filedAfter / filedBefore (ISO 8601 date-time, optional): filed-date range
  - page (number, default 1), pageSize (number, default 25, max 100)
  - response_format ('markdown'|'json', default 'markdown')

Returns: a page of claims plus pagination metadata (page, pageSize, totalCount).

Examples:
  - "What claims are under review for policy POL-1001?" -> status='under_review', policyNumber='POL-1001'
  - "Show claims filed in the last week" -> filedAfter=<7 days ago ISO timestamp>

Don't use when: you already have a claimId and just need its detail (use claims_get_claim instead).`,
      inputSchema: ListClaimsSchema.shape,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    async (params) => {
      try {
        const data = await claimsApiRequest<PaginatedResponse<Claim>>("/claims", "GET", undefined, {
          params: {
            status: params.status,
            policyNumber: params.policyNumber,
            claimantId: params.claimantId,
            filedAfter: params.filedAfter,
            filedBefore: params.filedBefore,
            page: params.page,
            pageSize: params.pageSize,
          },
        });

        const hasMore = data.page * data.pageSize < data.totalCount;
        const structured = {
          page: data.page,
          pageSize: data.pageSize,
          totalCount: data.totalCount,
          hasMore,
          nextPage: hasMore ? data.page + 1 : undefined,
          claims: data.data,
        };

        const { text } = renderText(params.response_format, structured, () => {
          if (!data.data.length) return "No claims matched the given filters.";
          const lines = [
            `# Claims (page ${data.page} of ${Math.max(1, Math.ceil(data.totalCount / data.pageSize))}, ${data.totalCount} total)`,
            "",
          ];
          for (const c of data.data) lines.push(claimToMarkdown(c), "");
          if (hasMore) lines.push(`_More results available — call again with page=${data.page + 1}._`);
          return lines.join("\n");
        });

        return { content: [{ type: "text", text }], structuredContent: structured };
      } catch (error) {
        return { isError: true, content: [{ type: "text", text: formatToolError(error) }] };
      }
    }
  );

  // --- claims_create_claim ---------------------------------------------
  const CreateClaimSchema = z
    .object({
      policyNumber: z.string().min(1).describe("The policy this claim is filed against, e.g. 'POL-1001'"),
      claimantId: z.string().min(1).describe("ID of a claimant already registered via claims_create_claimant"),
      claimType: z.string().min(1).describe("Claim type, e.g. 'auto_glass', 'homeowners_water_damage_small'"),
      incidentDate: z.string().describe("Date of the incident, ISO 8601 (YYYY-MM-DD)"),
      description: z.string().min(1).max(5000).describe("Description of the loss/incident"),
      filedAmount: z.number().min(0).describe("Amount being claimed"),
      currency: z.string().length(3).default("USD").describe("ISO 4217 currency code"),
      idempotencyKey: z
        .string()
        .optional()
        .describe("Optional client-supplied key so a retried submission does not create a duplicate claim"),
      response_format: responseFormatField,
    })
    .strict();

  server.registerTool(
    "claims_create_claim",
    {
      title: "File a New Claim",
      description: `Submit a new claim against a policy on behalf of a claimant.

This is a WRITE operation. It creates a new claim in status 'submitted'. Use
claims_check_policy_coverage first if you want to sanity-check coverage
before filing.

Args:
  - policyNumber, claimantId, claimType, incidentDate, description, filedAmount (all required)
  - currency (default 'USD')
  - idempotencyKey (optional): supply a stable key to make retries safe

Returns: the newly created Claim object, including its generated claimId.

Don't use when: the claimant isn't registered yet (call claims_create_claimant first).`,
      inputSchema: CreateClaimSchema.shape,
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    async (params) => {
      try {
        const { response_format, ...body } = params;
        const claim = await claimsApiRequest<Claim>("/claims", "POST", body);
        const { text } = renderText(response_format, claim, () => claimToMarkdown(claim));
        return { content: [{ type: "text", text }], structuredContent: claim };
      } catch (error) {
        return { isError: true, content: [{ type: "text", text: formatToolError(error) }] };
      }
    }
  );

  // --- claims_get_claim --------------------------------------------------
  const GetClaimSchema = z
    .object({
      claimId: claimIdField,
      response_format: responseFormatField,
    })
    .strict();

  server.registerTool(
    "claims_get_claim",
    {
      title: "Get Claim Detail",
      description: `Fetch full detail for a single claim by ID.

This is a READ-ONLY operation.

Args:
  - claimId (string, required): e.g. 'CLM-8841'
  - response_format ('markdown'|'json', default 'markdown')

Returns: the Claim object (status, amounts, adjuster, tags, timestamps).

Error handling:
  - Returns "Not found" if the claim does not exist.`,
      inputSchema: GetClaimSchema.shape,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    async ({ claimId, response_format }) => {
      try {
        const claim = await claimsApiRequest<Claim>(`/claims/${encodeURIComponent(claimId)}`);
        const { text } = renderText(response_format, claim, () => claimToMarkdown(claim));
        return { content: [{ type: "text", text }], structuredContent: claim };
      } catch (error) {
        return { isError: true, content: [{ type: "text", text: formatToolError(error) }] };
      }
    }
  );

  // --- claims_update_claim -----------------------------------------------
  const UpdateClaimSchema = z
    .object({
      claimId: claimIdField,
      description: z.string().min(1).max(5000).optional().describe("New description text"),
      tags: z.array(z.string()).optional().describe("Replacement list of tags for the claim"),
      response_format: responseFormatField,
    })
    .strict();

  server.registerTool(
    "claims_update_claim",
    {
      title: "Update Claim Details",
      description: `Update mutable fields (description, tags) on an existing claim.

This is a WRITE operation but does NOT change claim status — use
claims_transition_status for status changes (submit/approve/deny/close).

Args:
  - claimId (string, required)
  - description (string, optional)
  - tags (string array, optional): replaces the existing tag list

Returns: the updated Claim object.

Error handling:
  - Returns a conflict error if the claim is already 'closed' (immutable).`,
      inputSchema: UpdateClaimSchema.shape,
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    async ({ claimId, response_format, ...body }) => {
      try {
        const claim = await claimsApiRequest<Claim>(
          `/claims/${encodeURIComponent(claimId)}`,
          "PATCH",
          body
        );
        const { text } = renderText(response_format, claim, () => claimToMarkdown(claim));
        return { content: [{ type: "text", text }], structuredContent: claim };
      } catch (error) {
        return { isError: true, content: [{ type: "text", text: formatToolError(error) }] };
      }
    }
  );
}

export { claimToMarkdown };
