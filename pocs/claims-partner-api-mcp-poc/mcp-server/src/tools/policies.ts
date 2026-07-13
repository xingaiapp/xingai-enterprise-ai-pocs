import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { claimsApiRequest, formatToolError } from "../services/api-client.js";
import { renderText, money } from "../services/format.js";
import { responseFormatField } from "../schemas/common.js";
import type { CoverageCheckResult, Policy } from "../types.js";

function policyToMarkdown(p: Policy): string {
  const lines = [
    `## ${p.policyNumber} — ${p.policyType} (${p.status})`,
    `- **Holder**: ${p.holderName}`,
    `- **State**: ${p.state}`,
    `- **Effective**: ${p.effectiveDate} → ${p.expirationDate}`,
    `- **Coverages**:`,
  ];
  for (const [name, cov] of Object.entries(p.coverages)) {
    lines.push(`  - ${name}: limit ${money(cov.limit)}, deductible ${money(cov.deductible)}`);
  }
  return lines.join("\n");
}

export function registerPolicyTools(server: McpServer): void {
  // --- claims_get_policy ---------------------------------------------------
  const GetPolicySchema = z
    .object({
      policyNumber: z.string().min(1).describe("Policy number, e.g. 'POL-1001'"),
      response_format: responseFormatField,
    })
    .strict();

  server.registerTool(
    "claims_get_policy",
    {
      title: "Get Policy Detail",
      description: `Fetch a policy's detail and coverage limits/deductibles.

This is a READ-ONLY operation.

Args:
  - policyNumber (string, required)

Returns: the Policy object (type, holder, state, effective dates, per-coverage limit/deductible).`,
      inputSchema: GetPolicySchema.shape,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    async ({ policyNumber, response_format }) => {
      try {
        const policy = await claimsApiRequest<Policy>(`/policies/${encodeURIComponent(policyNumber)}`);
        const { text } = renderText(response_format, policy, () => policyToMarkdown(policy));
        return { content: [{ type: "text", text }], structuredContent: policy };
      } catch (error) {
        return { isError: true, content: [{ type: "text", text: formatToolError(error) }] };
      }
    }
  );

  // --- claims_check_policy_coverage ----------------------------------------
  const CheckCoverageSchema = z
    .object({
      policyNumber: z.string().min(1).describe("Policy number, e.g. 'POL-1001'"),
      claimType: z.string().min(1).describe("Claim type to check, e.g. 'auto_glass'"),
      amount: z.number().min(0).describe("Amount to check against coverage limits/deductible"),
      response_format: responseFormatField,
    })
    .strict();

  server.registerTool(
    "claims_check_policy_coverage",
    {
      title: "Check Policy Coverage",
      description: `Check whether a claim type/amount falls within a policy's coverage before filing.

This is a READ-ONLY operation — it does not file a claim, only estimates coverage.

Args:
  - policyNumber, claimType, amount (all required)

Returns: covered (boolean), coverageLimit, deductible, estimatedPayout, and explanatory notes.

Examples:
  - "Would a $1,850 water damage claim be covered under POL-2002?" -> claimType='water_damage', amount=1850`,
      inputSchema: CheckCoverageSchema.shape,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    async ({ policyNumber, claimType, amount, response_format }) => {
      try {
        const result = await claimsApiRequest<CoverageCheckResult>(
          `/policies/${encodeURIComponent(policyNumber)}/coverage-check`,
          "GET",
          undefined,
          { params: { claimType, amount } }
        );
        const { text } = renderText(response_format, result, () =>
          [
            `# Coverage Check — ${policyNumber} / ${claimType}`,
            `- **Covered**: ${result.covered ? "Yes" : "No"}`,
            `- **Coverage limit**: ${money(result.coverageLimit)}`,
            `- **Deductible**: ${money(result.deductible)}`,
            `- **Estimated payout**: ${money(result.estimatedPayout)}`,
            ...(result.notes ? [`- **Notes**: ${result.notes}`] : []),
          ].join("\n")
        );
        return { content: [{ type: "text", text }], structuredContent: result };
      } catch (error) {
        return { isError: true, content: [{ type: "text", text: formatToolError(error) }] };
      }
    }
  );
}
