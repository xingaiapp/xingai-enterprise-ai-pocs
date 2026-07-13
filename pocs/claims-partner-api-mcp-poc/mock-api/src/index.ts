#!/usr/bin/env node
/**
 * Claims Mock API
 *
 * A minimal, in-memory stand-in for a real claims/policy administration
 * system, implementing the endpoints defined in ../claims-api-openapi.yaml.
 * Exists so this POC is actually runnable end-to-end without access to a
 * real carrier backend — see README "Not Production Yet" for everything
 * this intentionally skips (persistence, real auth, audit trail, etc).
 */

import express, { type NextFunction, type Request, type Response } from "express";
import { claimsRouter } from "./routes/claims.js";
import { statusRouter } from "./routes/status.js";
import { notesRouter } from "./routes/notes.js";
import { documentsRouter } from "./routes/documents.js";
import { claimantsRouter } from "./routes/claimants.js";
import { policiesRouter } from "./routes/policies.js";
import { paymentsRouter } from "./routes/payments.js";

const app = express();
app.use(express.json({ limit: "15mb" }));

// Mock auth: any non-empty Bearer token is accepted. This mock exists to
// let the MCP server's Authorization header wiring be exercised end-to-end;
// it does not check scopes and must never be treated as real authentication.
app.use((req: Request, res: Response, next: NextFunction) => {
  if (req.path === "/healthz") return next();
  const auth = req.header("authorization");
  if (!auth?.startsWith("Bearer ") || auth.length <= "Bearer ".length) {
    return res.status(401).json({ detail: "Missing or empty Authorization: Bearer <token> header" });
  }
  next();
});

app.use(claimsRouter);
app.use(statusRouter);
app.use(notesRouter);
app.use(documentsRouter);
app.use(claimantsRouter);
app.use(policiesRouter);
app.use(paymentsRouter);

app.get("/healthz", (_req, res) => res.status(200).json({ status: "ok" }));

app.use((_req: Request, res: Response) => {
  res.status(404).json({ detail: "No such route on the claims mock API" });
});

// eslint-disable-next-line @typescript-eslint/no-unused-vars
app.use((err: unknown, _req: Request, res: Response, _next: NextFunction) => {
  console.error("Unhandled error in claims-mock-api:", err);
  res.status(500).json({ detail: "Internal error in claims mock API" });
});

const port = parseInt(process.env.PORT ?? "4000", 10);
app.listen(port, () => {
  console.error(`Claims mock API running on http://localhost:${port}`);
});
