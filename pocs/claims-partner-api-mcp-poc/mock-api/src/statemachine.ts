import type { ClaimStatus } from "./types.js";

/**
 * Legal claim status transitions. Kept as a simple adjacency map so the
 * illegality of e.g. submitted -> in_payment is enforced by the mock and
 * demonstrable in the POC's demo script, not just assumed.
 */
export const LEGAL_TRANSITIONS: Record<ClaimStatus, ClaimStatus[]> = {
  submitted: ["under_review", "closed"],
  under_review: ["approved", "denied", "closed"],
  approved: ["in_payment", "closed"],
  denied: ["closed", "reopened"],
  in_payment: ["closed"],
  closed: ["reopened"],
  reopened: ["under_review", "closed"],
};

export function isLegalTransition(from: ClaimStatus, to: ClaimStatus): boolean {
  return LEGAL_TRANSITIONS[from]?.includes(to) ?? false;
}
