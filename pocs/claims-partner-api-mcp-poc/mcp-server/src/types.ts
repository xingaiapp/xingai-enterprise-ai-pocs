// Mirrors the schemas in ../../claims-api-openapi.yaml

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
  // Index signature lets Claim be passed directly as CallToolResult.structuredContent
  [key: string]: unknown;
}

export interface PaginatedResponse<T> {
  data: T[];
  page: number;
  pageSize: number;
  totalCount: number;
}

export interface StatusEvent {
  eventId: string;
  claimId: string;
  fromStatus: ClaimStatus;
  toStatus: ClaimStatus;
  reason: string | null;
  actorId: string;
  occurredAt: string;
  [key: string]: unknown;
}

export interface Note {
  noteId: string;
  claimId: string;
  authorId: string;
  authorType: "adjuster" | "third_party" | "system";
  body: string;
  visibility: "internal" | "external";
  createdAt: string;
  [key: string]: unknown;
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
  [key: string]: unknown;
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
  [key: string]: unknown;
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
  [key: string]: unknown;
}

export interface CoverageCheckResult {
  covered: boolean;
  coverageLimit: number;
  deductible: number;
  estimatedPayout: number;
  notes: string;
  [key: string]: unknown;
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
  [key: string]: unknown;
}
