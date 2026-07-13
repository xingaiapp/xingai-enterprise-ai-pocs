import { Router } from "express";
import { claims, nextNoteId, notes, now } from "../data.js";
import type { Note } from "../types.js";

export const notesRouter = Router();

notesRouter.get("/claims/:claimId/notes", (req, res) => {
  const claim = claims.get(req.params.claimId.toUpperCase());
  if (!claim) return res.status(404).json({ detail: `No claim found: ${req.params.claimId}` });

  const visibility = (req.query.visibility as string) ?? "external";
  let list = notes.get(claim.claimId) ?? [];
  if (visibility !== "all") list = list.filter((n) => n.visibility === visibility);
  res.json(list);
});

notesRouter.post("/claims/:claimId/notes", (req, res) => {
  const claim = claims.get(req.params.claimId.toUpperCase());
  if (!claim) return res.status(404).json({ detail: `No claim found: ${req.params.claimId}` });

  const { body, visibility } = req.body ?? {};
  if (!body) return res.status(400).json({ detail: "body is required" });

  const note: Note = {
    noteId: nextNoteId(),
    claimId: claim.claimId,
    authorId: "third-party-agent",
    authorType: "third_party",
    body,
    visibility: visibility ?? "external",
    createdAt: now(),
  };
  const list = notes.get(claim.claimId) ?? [];
  list.push(note);
  notes.set(claim.claimId, list);
  res.status(201).json(note);
});
