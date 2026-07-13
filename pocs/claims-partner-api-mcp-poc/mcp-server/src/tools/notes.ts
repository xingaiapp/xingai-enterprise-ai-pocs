import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { claimsApiRequest, formatToolError } from "../services/api-client.js";
import { renderText, humanDate } from "../services/format.js";
import { claimIdField, responseFormatField } from "../schemas/common.js";
import type { Note } from "../types.js";

export function registerNoteTools(server: McpServer): void {
  // --- claims_list_notes ---------------------------------------------
  const ListNotesSchema = z
    .object({
      claimId: claimIdField,
      visibility: z
        .enum(["internal", "external", "all"])
        .default("external")
        .describe("Which notes to include; third parties should normally only see 'external'"),
      response_format: responseFormatField,
    })
    .strict();

  server.registerTool(
    "claims_list_notes",
    {
      title: "List Claim Notes",
      description: `List notes/communications logged against a claim.

This is a READ-ONLY operation.

Args:
  - claimId (string, required)
  - visibility ('internal'|'external'|'all', default 'external')

Returns: an array of Note objects (author, body, visibility, createdAt), oldest first.`,
      inputSchema: ListNotesSchema.shape,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    async ({ claimId, visibility, response_format }) => {
      try {
        const notes = await claimsApiRequest<Note[]>(
          `/claims/${encodeURIComponent(claimId)}/notes`,
          "GET",
          undefined,
          { params: { visibility } }
        );
        const structured = { claimId, notes };
        const { text } = renderText(response_format, structured, () => {
          if (!notes.length) return `No notes found for ${claimId}.`;
          const lines = [`# Notes — ${claimId}`, ""];
          for (const n of notes) {
            lines.push(`- **${humanDate(n.createdAt)}** (${n.authorType} ${n.authorId}): ${n.body}`);
          }
          return lines.join("\n");
        });
        return { content: [{ type: "text", text }], structuredContent: structured };
      } catch (error) {
        return { isError: true, content: [{ type: "text", text: formatToolError(error) }] };
      }
    }
  );

  // --- claims_add_note ---------------------------------------------------
  const AddNoteSchema = z
    .object({
      claimId: claimIdField,
      body: z.string().min(1).max(5000).describe("Note text"),
      visibility: z
        .enum(["internal", "external"])
        .default("external")
        .describe("Whether the note is visible to the claimant/external parties"),
      response_format: responseFormatField,
    })
    .strict();

  server.registerTool(
    "claims_add_note",
    {
      title: "Add Claim Note",
      description: `Add a note or communication entry to a claim's timeline.

This is a WRITE operation. It does not change claim status.

Args:
  - claimId (string, required)
  - body (string, required, max 5000 chars)
  - visibility ('internal'|'external', default 'external')

Returns: the newly created Note object.`,
      inputSchema: AddNoteSchema.shape,
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: false,
        openWorldHint: true,
      },
    },
    async ({ claimId, response_format, ...body }) => {
      try {
        const note = await claimsApiRequest<Note>(
          `/claims/${encodeURIComponent(claimId)}/notes`,
          "POST",
          body
        );
        const { text } = renderText(response_format, note, () => `Note added to ${claimId}: ${note.body}`);
        return { content: [{ type: "text", text }], structuredContent: note };
      } catch (error) {
        return { isError: true, content: [{ type: "text", text: formatToolError(error) }] };
      }
    }
  );
}
