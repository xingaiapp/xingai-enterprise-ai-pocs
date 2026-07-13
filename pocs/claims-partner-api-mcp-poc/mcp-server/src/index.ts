#!/usr/bin/env node
/**
 * Claims MCP Server
 *
 * Exposes the Claims Business API (see ../claims-api-openapi.yaml) to
 * third-party AI agents: claim intake and lookup, status transitions,
 * notes, documents, policy/coverage checks, claimant management, and
 * settlement payments.
 *
 * Auth: this server calls the Claims API with a bearer token read from
 * CLAIMS_API_TOKEN. In production, front this server itself with OAuth2.1
 * (see the xingai claims-mcp-oauth-poc reference project for that pattern)
 * so each third party authenticates to *this* MCP server with its own
 * scoped token, which you then exchange/pass through to the upstream API.
 */

import express from "express";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";

import { registerClaimsTools } from "./tools/claims.js";
import { registerStatusTools } from "./tools/status.js";
import { registerNoteTools } from "./tools/notes.js";
import { registerDocumentTools } from "./tools/documents.js";
import { registerClaimantTools } from "./tools/claimants.js";
import { registerPolicyTools } from "./tools/policies.js";
import { registerPaymentTools } from "./tools/payments.js";

function buildServer(): McpServer {
  const server = new McpServer({
    name: "claims-mcp-server",
    version: "1.0.0",
  });

  registerClaimsTools(server);
  registerStatusTools(server);
  registerNoteTools(server);
  registerDocumentTools(server);
  registerClaimantTools(server);
  registerPolicyTools(server);
  registerPaymentTools(server);

  return server;
}

function requireEnv(): void {
  if (!process.env.CLAIMS_API_TOKEN) {
    console.error(
      "ERROR: CLAIMS_API_TOKEN environment variable is required (see .env.example)."
    );
    process.exit(1);
  }
}

async function runStdio(): Promise<void> {
  requireEnv();
  const server = buildServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Claims MCP server running via stdio");
}

async function runHttp(): Promise<void> {
  requireEnv();
  const app = express();
  app.use(express.json({ limit: "15mb" })); // headroom over the 10MB base64 doc cap

  app.post("/mcp", async (req, res) => {
    // Stateless: a fresh server + transport per request avoids cross-request
    // state leakage and request-ID collisions across concurrent third parties.
    const server = buildServer();
    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: undefined,
      enableJsonResponse: true,
    });
    res.on("close", () => {
      transport.close();
      server.close();
    });
    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
  });

  app.get("/healthz", (_req, res) => res.status(200).json({ status: "ok" }));

  const port = parseInt(process.env.PORT ?? "3000", 10);
  app.listen(port, () => {
    console.error(`Claims MCP server running on http://localhost:${port}/mcp`);
  });
}

const transport = process.env.TRANSPORT ?? "stdio";
if (transport === "http") {
  runHttp().catch((error) => {
    console.error("Server error:", error);
    process.exit(1);
  });
} else {
  runStdio().catch((error) => {
    console.error("Server error:", error);
    process.exit(1);
  });
}
