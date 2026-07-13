import { Router } from "express";
import { claims, nextClaimId, now } from "../data.js";
import type { Claim } from "../types.js";

export const claimsRouter = Router();

claimsRouter.get("/claims", (req, res) => {
  const { status, policyNumber, claimantId, filedAfter, filedBefore } = req.query as Record<
    string,
    string | undefined
  >;
  const page = Math.max(1, Number(req.query.page ?? 1));
  const pageSize = Math.min(100, Math.max(1, Number(req.query.pageSize ?? 25)));

  let all = [...claims.values()];
  if (status) all = all.filter((c) => c.status === status);
  if (policyNumber) all = all.filter((c) => c.policyNumber === policyNumber);
  if (claimantId) all = all.filter((c) => c.claimantId === claimantId);
  if (filedAfter) all = all.filter((c) => c.createdAt >= filedAfter);
  if (filedBefore) all = all.filter((c) => c.createdAt < filedBefore);

  all.sort((a, b) => a.createdAt.localeCompare(b.createdAt));
  const totalCount = all.length;
  const start = (page - 1) * pageSize;
  const data = all.slice(start, start + pageSize);

  res.json({ data, page, pageSize, totalCount });
});

claimsRouter.post("/claims", (req, res) => {
  const body = req.body ?? {};
  const required = ["policyNumber", "claimantId", "claimType", "incidentDate", "description", "filedAmount"];
  for (const field of required) {
    if (body[field] === undefined || body[field] === null) {
      return res.status(400).json({ detail: `Missing required field: ${field}` });
    }
  }

  const ts = now();
  const claim: Claim = {
    claimId: nextClaimId(),
    policyNumber: body.policyNumber,
    claimantId: body.claimantId,
    claimType: body.claimType,
    status: "submitted",
    description: body.description,
    incidentDate: body.incidentDate,
    filedAmount: body.filedAmount,
    approvedAmount: null,
    currency: body.currency ?? "USD",
    adjusterId: null,
    tags: [],
    createdAt: ts,
    updatedAt: ts,
  };
  claims.set(claim.claimId, claim);
  res.status(201).json(claim);
});

claimsRouter.get("/claims/:claimId", (req, res) => {
  const claim = claims.get(req.params.claimId.toUpperCase());
  if (!claim) return res.status(404).json({ detail: `No claim found: ${req.params.claimId}` });
  res.json(claim);
});

claimsRouter.patch("/claims/:claimId", (req, res) => {
  const claim = claims.get(req.params.claimId.toUpperCase());
  if (!claim) return res.status(404).json({ detail: `No claim found: ${req.params.claimId}` });
  if (claim.status === "closed") {
    return res.status(409).json({ detail: `Claim ${claim.claimId} is closed and no longer mutable` });
  }
  const { description, tags } = req.body ?? {};
  if (description !== undefined) claim.description = description;
  if (tags !== undefined) claim.tags = tags;
  claim.updatedAt = now();
  res.json(claim);
});
