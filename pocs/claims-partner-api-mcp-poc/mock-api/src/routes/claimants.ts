import { Router } from "express";
import { claimants, nextClaimantId } from "../data.js";
import type { Claimant } from "../types.js";

export const claimantsRouter = Router();

claimantsRouter.post("/claimants", (req, res) => {
  const { name, email, phone, address } = req.body ?? {};
  if (!name || !email) return res.status(400).json({ detail: "name and email are required" });

  const claimant: Claimant = { claimantId: nextClaimantId(), name, email, phone, address };
  claimants.set(claimant.claimantId, claimant);
  res.status(201).json(claimant);
});

claimantsRouter.get("/claimants/:claimantId", (req, res) => {
  const claimant = claimants.get(req.params.claimantId.toUpperCase());
  if (!claimant) return res.status(404).json({ detail: `No claimant found: ${req.params.claimantId}` });
  res.json(claimant);
});
