import { Router } from "express";
import {
  claims,
  idempotencyKeys,
  nextEventId,
  nextPaymentId,
  now,
  payments,
  paymentsByClaim,
  statusEvents,
} from "../data.js";
import type { Payment, StatusEvent } from "../types.js";

export const paymentsRouter = Router();

paymentsRouter.get("/claims/:claimId/payments", (req, res) => {
  const claim = claims.get(req.params.claimId.toUpperCase());
  if (!claim) return res.status(404).json({ detail: `No claim found: ${req.params.claimId}` });
  const ids = paymentsByClaim.get(claim.claimId) ?? [];
  res.json(ids.map((id) => payments.get(id)).filter(Boolean));
});

paymentsRouter.post("/claims/:claimId/payments", (req, res) => {
  const claim = claims.get(req.params.claimId.toUpperCase());
  if (!claim) return res.status(404).json({ detail: `No claim found: ${req.params.claimId}` });

  const idempotencyKey = req.header("Idempotency-Key");
  if (!idempotencyKey) return res.status(400).json({ detail: "Idempotency-Key header is required" });

  const existingPaymentId = idempotencyKeys.get(idempotencyKey);
  if (existingPaymentId) {
    // Same key seen before: return the original payment instead of creating a
    // second one — this is the behavior claims_create_payment's idempotency
    // guarantee depends on.
    return res.status(201).json(payments.get(existingPaymentId));
  }

  if (claim.status !== "approved") {
    return res.status(409).json({
      detail: `Claim ${claim.claimId} is not in 'approved' status (currently '${claim.status}') — cannot issue payment`,
    });
  }

  const { amount, currency, method, payeeName } = req.body ?? {};
  if (!amount || !method || !payeeName) {
    return res.status(400).json({ detail: "amount, method, and payeeName are required" });
  }

  const payment: Payment = {
    paymentId: nextPaymentId(),
    claimId: claim.claimId,
    amount,
    currency: currency ?? "USD",
    method,
    payeeName,
    status: "issued",
    idempotencyKey,
    issuedAt: now(),
    createdAt: now(),
  };
  payments.set(payment.paymentId, payment);
  idempotencyKeys.set(idempotencyKey, payment.paymentId);
  const list = paymentsByClaim.get(claim.claimId) ?? [];
  list.push(payment.paymentId);
  paymentsByClaim.set(claim.claimId, list);

  const event: StatusEvent = {
    eventId: nextEventId(),
    claimId: claim.claimId,
    fromStatus: claim.status,
    toStatus: "in_payment",
    reason: `Settlement payment ${payment.paymentId} issued`,
    actorId: "third-party-agent",
    occurredAt: now(),
  };
  const history = statusEvents.get(claim.claimId) ?? [];
  history.push(event);
  statusEvents.set(claim.claimId, history);

  claim.status = "in_payment";
  claim.updatedAt = event.occurredAt;

  res.status(201).json(payment);
});

paymentsRouter.get("/payments/:paymentId", (req, res) => {
  const payment = payments.get(req.params.paymentId.toUpperCase());
  if (!payment) return res.status(404).json({ detail: `No payment found: ${req.params.paymentId}` });
  res.json(payment);
});
