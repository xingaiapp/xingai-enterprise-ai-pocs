import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { claimsApiRequest, formatToolError } from "../services/api-client.js";
import { renderText } from "../services/format.js";
import { responseFormatField } from "../schemas/common.js";
import type { Claimant } from "../types.js";

const AddressSchema = z
  .object({
    line1: z.string().optional(),
    city: z.string().optional(),
    state: z.string().optional(),
    postalCode: z.string().optional(),
    country: z.string().optional(),
  })
  .optional()
  .describe("Mailing address");

function claimantToMarkdown(c: Claimant): string {
  const addr = c.address
    ? [c.address.line1, c.address.city, c.address.state, c.address.postalCode, c.address.country]
        .filter(Boolean)
        .join(", ")
    : undefined;
  return [
    `## ${c.name} (${c.claimantId})`,
    `- **Email**: ${c.email}`,
    ...(c.phone ? [`- **Phone**: ${c.phone}`] : []),
    ...(addr ? [`- **Address**: ${addr}`] : []),
  ].join("\n");
}

export function registerClaimantTools(server: McpServer): void {
  // --- claims_create_claimant ----------------------------------------------
  const CreateClaimantSchema = z
    .object({
      name: z.string().min(1).describe("Full name of the claimant"),
      email: z.string().email().describe("Claimant's email address"),
      phone: z.string().optional().describe("Claimant's phone number"),
      address: AddressSchema,
      response_format: responseFormatField,
    })
    .strict();

  server.registerTool(
    "claims_create_claimant",
    {
      title: "Register a Claimant",
      description: `Register a new claimant profile so claims can be filed on their behalf.

This is a WRITE operation.

Args:
  - name, email (required)
  - phone, address (optional)

Returns: the created Claimant object, including its generated claimantId — pass
this to claims_create_claim.`,
      inputSchema: CreateClaimantSchema.shape,
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: false,
        openWorldHint: true,
      },
    },
    async ({ response_format, ...body }) => {
      try {
        const claimant = await claimsApiRequest<Claimant>("/claimants", "POST", body);
        const { text } = renderText(response_format, claimant, () => claimantToMarkdown(claimant));
        return { content: [{ type: "text", text }], structuredContent: claimant };
      } catch (error) {
        return { isError: true, content: [{ type: "text", text: formatToolError(error) }] };
      }
    }
  );

  // --- claims_get_claimant -------------------------------------------------
  const GetClaimantSchema = z
    .object({
      claimantId: z.string().min(1).describe("Claimant ID"),
      response_format: responseFormatField,
    })
    .strict();

  server.registerTool(
    "claims_get_claimant",
    {
      title: "Get Claimant Profile",
      description: `Fetch a claimant's profile by ID.

This is a READ-ONLY operation.

Args:
  - claimantId (string, required)

Returns: the Claimant object (name, email, phone, address).`,
      inputSchema: GetClaimantSchema.shape,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    async ({ claimantId, response_format }) => {
      try {
        const claimant = await claimsApiRequest<Claimant>(`/claimants/${encodeURIComponent(claimantId)}`);
        const { text } = renderText(response_format, claimant, () => claimantToMarkdown(claimant));
        return { content: [{ type: "text", text }], structuredContent: claimant };
      } catch (error) {
        return { isError: true, content: [{ type: "text", text: formatToolError(error) }] };
      }
    }
  );
}
