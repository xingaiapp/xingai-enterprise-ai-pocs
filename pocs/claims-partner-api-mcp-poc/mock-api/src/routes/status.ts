import { Router } from "express";
import { claims, nextEventId, now, statusEvents } from "../data.js";
import { isLegalTransition } from "../statemachine.js";
import type { ClaimStatus, StatusEvent } from "../types.js";

export const statusRouter = Router();

statusRouter.post("/claims/:claimId/status", (req, res) => {
  const claim = claims.get(req.params.claimId.toUpperCase());
  if (!claim) return res.status(404).json({ detail: `No claim found: ${req.params.claimId}` });

  const { toStatus, reason, approvedAmount } = (req.body ?? {}) as {
    toStatus?: ClaimStatus;
    reason?: string;
    approvedAmount?: number;
  };

  if (!toStatus) return res.status(400).json({ detail: "toStatus is required" });

  if (!isLegalTransition(claim.status, toStatus)) {
    return res.status(409).json({
      detail: `Illegal transition: cannot move claim ${claim.claimId} from '${claim.status}' to '${toStatus}'`,
    });
  }

  if (toStatus === "denied" && !reason) {
    return res.status(400).json({ detail: "reason is required when denying a claim" });
  }
  if (toStatus === "approved" && (approvedAmount === undefined || approvedAmount === null)) {
    return res.status(400).json({ detail: "approvedAmount is required when approving a claim" });
  }

  const event: StatusEvent = {
    eventId: nextEventId(),
    claimId: claim.claimId,
    fromStatus: claim.status,
    toStatus,
    reason: reason ?? null,
    actorId: "third-party-agent",
    occurredAt: now(),
  };
  const history = statusEvents.get(claim.claimId) ?? [];
  history.push(event);
  statusEvents.set(claim.claimId, history);

  claim.status = toStatus;
  if (toStatus === "approved") claim.approvedAmount = approvedAmount!;
  claim.updatedAt = event.occurredAt;

  res.json(claim);
});

statusRouter.get("/claims/:claimId/status-history", (req, res) => {
  const claim = claims.get(req.params.claimId.toUpperCase());
  if (!claim) return res.status(404).json({ detail: `No claim found: ${req.params.claimId}` });
  res.json(statusEvents.get(claim.claimId) ?? []);
});
