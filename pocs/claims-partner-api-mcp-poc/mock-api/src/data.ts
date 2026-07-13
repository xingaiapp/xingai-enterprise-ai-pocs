import type { Claim, Claimant, ClaimDocument, Note, Payment, Policy, StatusEvent } from "./types.js";

/**
 * In-memory fixtures standing in for a real claims/policy administration
 * system. Seed data intentionally reuses the same policy numbers
 * (POL-1001/2002/3003) and claimant names as the sibling
 * `pocs/claims-mcp-oauth-poc` fixtures for narrative continuity across POCs
 * in this repo — see that POC's `mcp_server/policies.py`.
 *
 * Everything here is a plain in-memory object. Restarting the process wipes
 * all state — see README "Not Production Yet".
 */

export const claimants = new Map<string, Claimant>([
  [
    "CLT-1",
    {
      claimantId: "CLT-1",
      name: "Alex Rivera",
      email: "alex.rivera@example.com",
      phone: "+1-555-0101",
      address: { line1: "12 Elm St", city: "Sacramento", state: "CA", postalCode: "95814", country: "US" },
    },
  ],
  [
    "CLT-2",
    {
      claimantId: "CLT-2",
      name: "Jordan Lee",
      email: "jordan.lee@example.com",
      phone: "+1-555-0102",
      address: { line1: "88 Oak Ave", city: "Austin", state: "TX", postalCode: "78701", country: "US" },
    },
  ],
  [
    "CLT-3",
    {
      claimantId: "CLT-3",
      name: "Morgan Diaz",
      email: "morgan.diaz@example.com",
      phone: "+1-555-0103",
      address: { line1: "400 Pine Rd", city: "Fresno", state: "CA", postalCode: "93701", country: "US" },
    },
  ],
]);

export const policies = new Map<string, Policy>([
  [
    "POL-1001",
    {
      policyNumber: "POL-1001",
      policyType: "auto_comprehensive",
      holderName: "Alex Rivera",
      state: "CA",
      effectiveDate: "2026-01-01",
      expirationDate: "2027-01-01",
      status: "active",
      coverages: {
        collision: { limit: 25_000, deductible: 500 },
        comprehensive: { limit: 25_000, deductible: 250 },
        glass: { limit: 1_500, deductible: 0 },
      },
    },
  ],
  [
    "POL-2002",
    {
      policyNumber: "POL-2002",
      policyType: "homeowners",
      holderName: "Jordan Lee",
      state: "TX",
      effectiveDate: "2026-02-01",
      expirationDate: "2027-02-01",
      status: "active",
      coverages: {
        dwelling: { limit: 350_000, deductible: 1_000 },
        water_damage: { limit: 10_000, deductible: 500 },
      },
    },
  ],
  [
    "POL-3003",
    {
      policyNumber: "POL-3003",
      policyType: "auto_comprehensive",
      holderName: "Morgan Diaz",
      state: "CA",
      effectiveDate: "2026-01-15",
      expirationDate: "2027-01-15",
      status: "active",
      coverages: {
        collision: { limit: 40_000, deductible: 1_000 },
        comprehensive: { limit: 40_000, deductible: 500 },
      },
    },
  ],
]);

const now = () => new Date().toISOString();

export const claims = new Map<string, Claim>([
  [
    "CLM-8841",
    {
      claimId: "CLM-8841",
      policyNumber: "POL-1001",
      claimantId: "CLT-1",
      claimType: "auto_glass",
      status: "submitted",
      description: "Windshield cracked by road debris on I-5",
      incidentDate: "2026-07-08",
      filedAmount: 640.0,
      approvedAmount: null,
      currency: "USD",
      adjusterId: null,
      tags: [],
      createdAt: "2026-07-08T14:20:00Z",
      updatedAt: "2026-07-08T14:20:00Z",
    },
  ],
  [
    "CLM-8842",
    {
      claimId: "CLM-8842",
      policyNumber: "POL-2002",
      claimantId: "CLT-2",
      claimType: "homeowners_water_damage_small",
      status: "submitted",
      description: "Burst supply line under kitchen sink, minor cabinetry damage",
      incidentDate: "2026-07-09",
      filedAmount: 1_850.0,
      approvedAmount: null,
      currency: "USD",
      adjusterId: null,
      tags: [],
      createdAt: "2026-07-09T09:05:00Z",
      updatedAt: "2026-07-09T09:05:00Z",
    },
  ],
  [
    "CLM-9010",
    {
      claimId: "CLM-9010",
      policyNumber: "POL-3003",
      claimantId: "CLT-3",
      claimType: "auto_comprehensive_total_loss",
      status: "submitted",
      description: "Vehicle fire, total loss",
      incidentDate: "2026-07-10",
      filedAmount: 28_500.0,
      approvedAmount: null,
      currency: "USD",
      adjusterId: null,
      tags: [],
      createdAt: "2026-07-10T11:40:00Z",
      updatedAt: "2026-07-10T11:40:00Z",
    },
  ],
]);

export const statusEvents = new Map<string, StatusEvent[]>();
export const notes = new Map<string, Note[]>();
export const documents = new Map<string, ClaimDocument[]>();
export const payments = new Map<string, Payment>();
export const paymentsByClaim = new Map<string, string[]>();
export const idempotencyKeys = new Map<string, string>(); // idempotencyKey -> paymentId

let claimSeq = 9100;
let claimantSeq = 4;
let noteSeq = 1;
let docSeq = 1;
let eventSeq = 1;
let paymentSeq = 1;

export function nextClaimId(): string {
  return `CLM-${claimSeq++}`;
}
export function nextClaimantId(): string {
  return `CLT-${claimantSeq++}`;
}
export function nextNoteId(): string {
  return `NOTE-${String(noteSeq++).padStart(4, "0")}`;
}
export function nextDocumentId(): string {
  return `DOC-${String(docSeq++).padStart(4, "0")}`;
}
export function nextEventId(): string {
  return `EVT-${String(eventSeq++).padStart(4, "0")}`;
}
export function nextPaymentId(): string {
  return `PAY-${String(paymentSeq++).padStart(4, "0")}`;
}

export { now };
