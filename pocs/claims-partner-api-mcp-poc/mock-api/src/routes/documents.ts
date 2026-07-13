import { Router } from "express";
import { claims, documents, nextDocumentId, now } from "../data.js";
import type { ClaimDocument } from "../types.js";

export const documentsRouter = Router();

const MAX_DECODED_BYTES = 10 * 1024 * 1024; // 10MB

function signedDownloadUrl(claimId: string, documentId: string): string {
  const exp = Date.now() + 15 * 60 * 1000; // 15-minute mock signed URL
  return `https://mock-storage.local/claims/${claimId}/documents/${documentId}?exp=${exp}&sig=mock`;
}

documentsRouter.get("/claims/:claimId/documents", (req, res) => {
  const claim = claims.get(req.params.claimId.toUpperCase());
  if (!claim) return res.status(404).json({ detail: `No claim found: ${req.params.claimId}` });
  res.json(documents.get(claim.claimId) ?? []);
});

documentsRouter.post("/claims/:claimId/documents", (req, res) => {
  const claim = claims.get(req.params.claimId.toUpperCase());
  if (!claim) return res.status(404).json({ detail: `No claim found: ${req.params.claimId}` });

  const { fileName, docType, mimeType, sourceUrl, base64Content } = req.body ?? {};
  if (!fileName || !docType) {
    return res.status(400).json({ detail: "fileName and docType are required" });
  }
  if (!!sourceUrl === !!base64Content) {
    return res.status(400).json({ detail: "Provide exactly one of sourceUrl or base64Content" });
  }

  let sizeBytes = 0;
  if (base64Content) {
    sizeBytes = Buffer.from(base64Content, "base64").length;
    if (sizeBytes > MAX_DECODED_BYTES) {
      return res.status(413).json({ detail: "File exceeds the 10MB maximum allowed size" });
    }
  }

  const documentId = nextDocumentId();
  const doc: ClaimDocument = {
    documentId,
    claimId: claim.claimId,
    fileName,
    docType,
    mimeType: mimeType ?? "application/octet-stream",
    sizeBytes,
    downloadUrl: signedDownloadUrl(claim.claimId, documentId),
    uploadedBy: "third-party-agent",
    uploadedAt: now(),
  };
  const list = documents.get(claim.claimId) ?? [];
  list.push(doc);
  documents.set(claim.claimId, list);
  res.status(201).json(doc);
});

documentsRouter.get("/claims/:claimId/documents/:documentId", (req, res) => {
  const claim = claims.get(req.params.claimId.toUpperCase());
  if (!claim) return res.status(404).json({ detail: `No claim found: ${req.params.claimId}` });
  const doc = (documents.get(claim.claimId) ?? []).find((d) => d.documentId === req.params.documentId);
  if (!doc) return res.status(404).json({ detail: `No document found: ${req.params.documentId}` });
  // Refresh the signed URL each time, like a real object-storage presigned URL would be.
  res.json({ ...doc, downloadUrl: signedDownloadUrl(claim.claimId, doc.documentId) });
});
