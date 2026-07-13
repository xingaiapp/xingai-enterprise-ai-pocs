import { Router } from "express";
import { policies } from "../data.js";

export const policiesRouter = Router();

policiesRouter.get("/policies/:policyNumber", (req, res) => {
  const policy = policies.get(req.params.policyNumber.toUpperCase());
  if (!policy) return res.status(404).json({ detail: `No policy found: ${req.params.policyNumber}` });
  res.json(policy);
});

policiesRouter.get("/policies/:policyNumber/coverage-check", (req, res) => {
  const policy = policies.get(req.params.policyNumber.toUpperCase());
  if (!policy) return res.status(404).json({ detail: `No policy found: ${req.params.policyNumber}` });

  const claimType = String(req.query.claimType ?? "");
  const amount = Number(req.query.amount ?? 0);

  // Best-effort match: look for a coverage bucket whose name appears in the
  // claim type string (e.g. claimType="water_damage" -> coverages.water_damage).
  const matchKey = Object.keys(policy.coverages).find(
    (k) => claimType.includes(k) || k.includes(claimType)
  );
  const coverage = matchKey ? policy.coverages[matchKey] : undefined;

  if (!coverage) {
    return res.json({
      covered: false,
      coverageLimit: 0,
      deductible: 0,
      estimatedPayout: 0,
      notes: `No matching coverage bucket for claim type '${claimType}' on policy ${policy.policyNumber}.`,
    });
  }

  const withinLimit = amount <= coverage.limit;
  const estimatedPayout = withinLimit ? Math.max(0, amount - coverage.deductible) : coverage.limit;

  res.json({
    covered: withinLimit,
    coverageLimit: coverage.limit,
    deductible: coverage.deductible,
    estimatedPayout,
    notes: withinLimit
      ? `Within the '${matchKey}' coverage limit; deductible applied.`
      : `Amount exceeds the '${matchKey}' coverage limit of ${coverage.limit}.`,
  });
});
