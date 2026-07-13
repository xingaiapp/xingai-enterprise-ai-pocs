import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { claimsApiRequest, formatToolError } from "../services/api-client.js";
import { renderText, humanDate } from "../services/format.js";
import { claimIdField, responseFormatField } from "../schemas/common.js";
import type { ClaimDocument } from "../types.js";

const DocumentTypeEnum = z.enum([
  "photo",
  "invoice",
  "estimate",
  "police_report",
  "medical_record",
  "correspondence",
  "other",
]);

function docToLine(d: ClaimDocument): string {
  const sizeKb = (d.sizeBytes / 1024).toFixed(1);
  return `- **${d.fileName}** (${d.docType}, ${sizeKb} KB, uploaded ${humanDate(d.uploadedAt)} by ${d.uploadedBy}) — id: ${d.documentId}`;
}

export function registerDocumentTools(server: McpServer): void {
  // --- claims_list_documents ----------------------------------------------
  const ListDocsSchema = z
    .object({
      claimId: claimIdField,
      response_format: responseFormatField,
    })
    .strict();

  server.registerTool(
    "claims_list_documents",
    {
      title: "List Claim Documents",
      description: `List documents (photos, invoices, estimates, reports) attached to a claim.

This is a READ-ONLY operation. Download URLs are time-limited; call
claims_get_document again if a link has expired.

Args:
  - claimId (string, required)

Returns: an array of Document metadata objects (does not include file bytes).`,
      inputSchema: ListDocsSchema.shape,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    async ({ claimId, response_format }) => {
      try {
        const docs = await claimsApiRequest<ClaimDocument[]>(
          `/claims/${encodeURIComponent(claimId)}/documents`
        );
        const structured = { claimId, documents: docs };
        const { text } = renderText(response_format, structured, () => {
          if (!docs.length) return `No documents attached to ${claimId}.`;
          return [`# Documents — ${claimId}`, "", ...docs.map(docToLine)].join("\n");
        });
        return { content: [{ type: "text", text }], structuredContent: structured };
      } catch (error) {
        return { isError: true, content: [{ type: "text", text: formatToolError(error) }] };
      }
    }
  );

  // --- claims_upload_document ----------------------------------------------
  const UploadDocBaseSchema = z
    .object({
      claimId: claimIdField,
      fileName: z.string().min(1).describe("File name, e.g. 'repair_estimate.pdf'"),
      docType: DocumentTypeEnum.describe("Category of the document"),
      mimeType: z.string().optional().describe("MIME type, e.g. 'application/pdf' or 'image/jpeg'"),
      sourceUrl: z
        .string()
        .url()
        .optional()
        .describe("URL of an already-hosted file the API should fetch and store"),
      base64Content: z
        .string()
        .optional()
        .describe("Base64-encoded file bytes for small inline uploads (max 10MB decoded)"),
      response_format: responseFormatField,
    })
    .strict();

  // Cross-field validation (exactly one of sourceUrl/base64Content) is
  // enforced at runtime via .parse() in the handler below; the exposed
  // inputSchema uses the base object shape so the JSON schema stays simple.
  const UploadDocSchema = UploadDocBaseSchema.refine(
    (v) => !!v.sourceUrl !== !!v.base64Content,
    {
      message: "Provide exactly one of sourceUrl or base64Content, not both and not neither.",
    }
  );

  server.registerTool(
    "claims_upload_document",
    {
      title: "Upload Claim Document",
      description: `Attach a document (photo, invoice, estimate, report, correspondence) to a claim.

This is a WRITE operation. Provide exactly one of:
  - sourceUrl: a URL the API will fetch and store, or
  - base64Content: base64-encoded bytes for small files (<= 10MB decoded)

Args:
  - claimId, fileName, docType (required)
  - mimeType (optional but recommended)
  - sourceUrl OR base64Content (exactly one required)

Returns: the created Document metadata, including a time-limited downloadUrl.

Error handling:
  - Returns an error if both or neither of sourceUrl/base64Content are set.
  - Returns "too large" if the decoded file exceeds 10MB.`,
      inputSchema: UploadDocBaseSchema.shape,
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: false,
        openWorldHint: true,
      },
    },
    async (rawParams) => {
      try {
        const params = UploadDocSchema.parse(rawParams);
        const { claimId, response_format, ...body } = params;
        const doc = await claimsApiRequest<ClaimDocument>(
          `/claims/${encodeURIComponent(claimId)}/documents`,
          "POST",
          body
        );
        const { text } = renderText(response_format, doc, () => docToLine(doc));
        return { content: [{ type: "text", text }], structuredContent: doc };
      } catch (error) {
        return { isError: true, content: [{ type: "text", text: formatToolError(error) }] };
      }
    }
  );

  // --- claims_get_document -------------------------------------------------
  const GetDocSchema = z
    .object({
      claimId: claimIdField,
      documentId: z.string().min(1).describe("Document ID as returned by claims_list_documents"),
      response_format: responseFormatField,
    })
    .strict();

  server.registerTool(
    "claims_get_document",
    {
      title: "Get Claim Document",
      description: `Get metadata and a fresh time-limited download URL for a single claim document.

This is a READ-ONLY operation.

Args:
  - claimId, documentId (required)

Returns: the Document object including a fresh downloadUrl.`,
      inputSchema: GetDocSchema.shape,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    async ({ claimId, documentId, response_format }) => {
      try {
        const doc = await claimsApiRequest<ClaimDocument>(
          `/claims/${encodeURIComponent(claimId)}/documents/${encodeURIComponent(documentId)}`
        );
        const { text } = renderText(response_format, doc, () => `${docToLine(doc)}\n  Download: ${doc.downloadUrl}`);
        return { content: [{ type: "text", text }], structuredContent: doc };
      } catch (error) {
        return { isError: true, content: [{ type: "text", text: formatToolError(error) }] };
      }
    }
  );
}
