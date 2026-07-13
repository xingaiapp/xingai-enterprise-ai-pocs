// Mirrors ../../claims-api-openapi.yaml — kept independent from mcp-server/src/types.ts
// on purpose: in a real deployment these two services are owned by different teams
// and should not share a compiled type package.

export type ClaimStatus =
  | "submitted"
  | "under_review"
  | "approved"
  | "denied"
  | "in_payment"
  | "closed"
  | "reopened";

export type DocumentType =
  | "photo"
  | "invoice"
  | "estimate"
  | "police_report"
  | "medical_record"
  | "correspondence"
  | "other";

export interface Claim {
  claimId: string;
  policyNumber: string;
  claimantId: string;
  claimType: string;
  status: ClaimStatus;
  description: string;
  incidentDate: string;
  filedAmount: number;
  approvedAmount: number | null;
  currency: string;
  adjusterId: string | null;
  tags: string[];
  createdAt: string;
  updatedAt: string;
}

export interface StatusEvent {
  eventId: string;
  claimId: string;
  fromStatus: ClaimStatus;
  toStatus: ClaimStatus;
  reason: string | null;
  actorId: string;
  occurredAt: string;
}

export interface Note {
  noteId: string;
  claimId: string;
  authorId: string;
  authorType: "adjuster" | "third_party" | "system";
  body: string;
  visibility: "internal" | "external";
  createdAt: string;
}

export interface ClaimDocument {
  documentId: string;
  claimId: string;
  fileName: string;
  docType: DocumentType;
  mimeType: string;
  sizeBytes: number;
  downloadUrl: string;
  uploadedBy: string;
  uploadedAt: string;
}

export interface Claimant {
  claimantId: string;
  name: string;
  email: string;
  phone?: string;
  address?: {
    line1?: string;
    city?: string;
    state?: string;
    postalCode?: string;
    country?: string;
  };
}

export interface Policy {
  policyNumber: string;
  policyType: string;
  holderName: string;
  state: string;
  effectiveDate: string;
  expirationDate: string;
  status: "active" | "lapsed" | "cancelled";
  coverages: Record<string, { limit: number; deductible: number }>;
}

export interface Payment {
  paymentId: string;
  claimId: string;
  amount: number;
  currency: string;
  method: "ach" | "check" | "wire" | "card";
  payeeName: string;
  status: "pending" | "issued" | "failed" | "cancelled";
  idempotencyKey: string;
  issuedAt: string | null;
  createdAt: string;
}
