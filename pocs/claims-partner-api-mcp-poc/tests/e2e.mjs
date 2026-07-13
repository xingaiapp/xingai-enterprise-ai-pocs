#!/usr/bin/env node
/**
 * End-to-end smoke test for this POC's happy path, run against the two
 * already-running services (mcp-server on :3000, mock-api on :4000 — start
 * both first, e.g. via `docker compose up` or `npm run dev` in each
 * package). Exercises the full lifecycle a third-party agent would drive
 * through the MCP server: register a claimant, file a claim, check
 * coverage, walk the claim through status transitions, and issue a
 * settlement payment.
 *
 * This is intentionally a plain Node script (not a test framework) to keep
 * the POC's dependency surface small — see README "Not Production Yet" for
 * why this isn't a substitute for real test coverage.
 */

const MCP_URL = process.env.MCP_URL ?? "http://localhost:3000/mcp";

let rpcId = 1;

async function callTool(name, args) {
  const res = await fetch(MCP_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json, text/event-stream" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: rpcId++,
      method: "tools/call",
      params: { name, arguments: args },
    }),
  });
  const body = await res.json();
  if (body.error) {
    throw new Error(`tools/call ${name} failed: ${JSON.stringify(body.error)}`);
  }
  const result = body.result;
  if (result.isError) {
    throw new Error(`tool ${name} returned isError: ${JSON.stringify(result.content)}`);
  }
  return result.structuredContent;
}

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION FAILED: ${message}`);
}

async function main() {
  console.log("1. Registering a new claimant...");
  const claimant = await callTool("claims_create_claimant", {
    name: "Taylor Chen",
    email: "taylor.chen@example.com",
    response_format: "json",
  });
  assert(claimant.claimantId, "expected a generated claimantId");
  console.log(`   -> ${claimant.claimantId}`);

  console.log("2. Checking policy coverage before filing...");
  const coverage = await callTool("claims_check_policy_coverage", {
    policyNumber: "POL-1001",
    claimType: "glass",
    amount: 500,
    response_format: "json",
  });
  assert(coverage.covered === true, "expected the $500 glass claim to be covered under POL-1001");
  console.log(`   -> covered=${coverage.covered}, estimatedPayout=${coverage.estimatedPayout}`);

  console.log("3. Filing a new claim...");
  const claim = await callTool("claims_create_claim", {
    policyNumber: "POL-1001",
    claimantId: claimant.claimantId,
    claimType: "auto_glass",
    incidentDate: "2026-07-12",
    description: "Cracked windshield from a gravel truck on Hwy 50",
    filedAmount: 500,
    response_format: "json",
  });
  assert(claim.status === "submitted", `expected new claim to be 'submitted', got '${claim.status}'`);
  console.log(`   -> ${claim.claimId} (${claim.status})`);

  console.log("4. Adding a note...");
  const note = await callTool("claims_add_note", {
    claimId: claim.claimId,
    body: "Photos received from claimant, forwarding to fast-track review.",
    response_format: "json",
  });
  assert(note.noteId, "expected a generated noteId");
  console.log(`   -> ${note.noteId}`);

  console.log("5. Transitioning submitted -> under_review...");
  let updated = await callTool("claims_transition_status", {
    claimId: claim.claimId,
    toStatus: "under_review",
    response_format: "json",
  });
  assert(updated.status === "under_review", "expected status 'under_review'");

  console.log("6. Transitioning under_review -> approved...");
  updated = await callTool("claims_transition_status", {
    claimId: claim.claimId,
    toStatus: "approved",
    approvedAmount: 500,
    response_format: "json",
  });
  assert(updated.status === "approved", "expected status 'approved'");
  assert(updated.approvedAmount === 500, "expected approvedAmount to be recorded");

  console.log("7. Confirming an illegal transition is rejected (approved -> under_review)...");
  let illegalTransitionRejected = false;
  try {
    await callTool("claims_transition_status", {
      claimId: claim.claimId,
      toStatus: "under_review",
      response_format: "json",
    });
  } catch {
    illegalTransitionRejected = true;
  }
  assert(illegalTransitionRejected, "expected approved -> under_review to be rejected as illegal");
  console.log("   -> correctly rejected");

  console.log("8. Issuing settlement payment...");
  const payment = await callTool("claims_create_payment", {
    claimId: claim.claimId,
    amount: 500,
    method: "ach",
    payeeName: "Taylor Chen",
    response_format: "json",
  });
  assert(payment.status === "issued", `expected payment status 'issued', got '${payment.status}'`);
  console.log(`   -> ${payment.paymentId} (${payment.status})`);

  console.log("9. Verifying claim moved to in_payment...");
  const finalClaim = await callTool("claims_get_claim", { claimId: claim.claimId, response_format: "json" });
  assert(finalClaim.status === "in_payment", `expected claim status 'in_payment', got '${finalClaim.status}'`);

  console.log("10. Verifying status history recorded all transitions (including the payment-driven one)...");
  const history = await callTool("claims_list_status_history", {
    claimId: claim.claimId,
    response_format: "json",
  });
  assert(history.events.length === 3, `expected 3 status events, got ${history.events.length}`);

  console.log("\nAll checks passed.");
}

main().catch((err) => {
  console.error("\nE2E TEST FAILED:", err.message);
  process.exit(1);
});
