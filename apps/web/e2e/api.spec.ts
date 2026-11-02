import { expect, test, type APIRequestContext } from "@playwright/test";

import { signUp } from "./helpers";

const GOOD_BILL = "Service,EC2($)\n2026-09-01,100.00\n2026-10-01,150.00\n";
const NOT_A_BILL = "name,age\nAnn,30\n";
const UPLOAD_LIMIT_MB = 100;

function billFile(name: string, content: string | Buffer, mimeType = "text/csv") {
  return { multipart: { file: { name, mimeType, buffer: Buffer.from(content) } } };
}

async function waitForStatus(api: APIRequestContext, id: string, status: string) {
  await expect
    .poll(async () => (await (await api.get(`/api/documents/${id}`)).json()).status)
    .toBe(status);
}

/** Every route the API publishes must be listed here, so a new route cannot go untested. */
const TESTED_ROUTES = [
  "GET /api/health",
  "GET /api/me",
  "GET /api/auth/login",
  "GET /api/auth/callback",
  "POST /api/auth/logout",
  "GET /api/documents",
  "POST /api/documents",
  "POST /api/documents/sample",
  "GET /api/documents/{document_id}",
  "DELETE /api/documents/{document_id}",
  "POST /api/documents/{document_id}/reprocess",
  "GET /api/analytics/overview",
  "GET /api/analytics/compare",
  "GET /api/analytics/unusual",
];

test.describe("without signing in", () => {
  test("health is open to everyone", async ({ request }) => {
    const response = await request.get("/api/health");

    expect(response.status()).toBe(200);
    expect(await response.json()).toEqual({ status: "ok" });
  });

  test("the test list matches every route the API publishes", async ({ request }) => {
    const { paths } = await (await request.get("/api/openapi.json")).json();
    const published = Object.entries<Record<string, unknown>>(paths).flatMap(([path, methods]) =>
      Object.keys(methods).map((method) => `${method.toUpperCase()} ${path}`),
    );

    expect(published.sort()).toEqual([...TESTED_ROUTES].sort());
  });

  test("private routes all refuse a visitor", async ({ request }) => {
    const id = crypto.randomUUID();
    const responses = await Promise.all([
      request.get("/api/me"),
      request.post("/api/auth/logout"),
      request.get("/api/documents"),
      request.post("/api/documents", billFile("bill.csv", GOOD_BILL)),
      request.post("/api/documents/sample"),
      request.get(`/api/documents/${id}`),
      request.delete(`/api/documents/${id}`),
      request.post(`/api/documents/${id}/reprocess`),
      request.get("/api/analytics/overview"),
      request.get("/api/analytics/compare?first=2026-09-01&second=2026-10-01"),
      request.get("/api/analytics/unusual"),
    ]);

    expect(responses.map((response) => response.status())).toEqual(Array(11).fill(401));
    expect((await (await request.get("/api/me")).json()).error.code).toBe("not_authenticated");
  });

  test("login sends the visitor to Keycloak with PKCE", async ({ request }) => {
    const response = await request.get("/api/auth/login", { maxRedirects: 0 });
    const location = new URL(response.headers().location);

    expect(response.status()).toBe(302);
    expect(location.pathname).toContain("/protocol/openid-connect/auth");
    expect(location.searchParams.get("code_challenge_method")).toBe("S256");
    expect(location.searchParams.get("state")).toBeTruthy();
    expect(response.headers()["set-cookie"]).toContain("HttpOnly");
  });

  test("a login reply without the browser's cookie is refused", async ({ request }) => {
    const response = await request.get("/api/auth/callback?code=fake&state=fake", {
      maxRedirects: 0,
    });

    expect(response.status()).toBe(400);
    expect((await response.json()).error.code).toBe("login_failed");
  });

  test("a made-up session cookie is refused", async ({ request }) => {
    const response = await request.get("/api/me", {
      headers: { cookie: "costpilot_session=not-a-real-ticket" },
    });

    expect(response.status()).toBe(401);
  });
});

test("a signed-in user can use every endpoint", async ({ page, request }) => {
  await signUp(page, request);
  const api = page.request;
  let documentId = "";

  await test.step("GET /api/me", async () => {
    const me = await (await api.get("/api/me")).json();
    expect(me.display_name).toBe("Ann Lee");
    expect(me.role).toBe("owner");
    expect(me.workspace_name).toBe("My workspace");
    expect(me.account_url).toContain("/account");
  });

  await test.step("a new workspace is empty", async () => {
    expect(await (await api.get("/api/documents")).json()).toEqual([]);
    expect(await (await api.get("/api/analytics/overview")).json()).toBeNull();
    expect(await (await api.get("/api/analytics/unusual")).json()).toEqual([]);
  });

  await test.step("POST /api/documents", async () => {
    const response = await api.post("/api/documents", billFile("bill.csv", GOOD_BILL));
    expect(response.status()).toBe(201);
    const document = await response.json();
    documentId = document.id;
    expect(document.file_name).toBe("bill.csv");
    await waitForStatus(api, documentId, "processed");
  });

  await test.step("upload problems give clear errors", async () => {
    const duplicate = await api.post("/api/documents", billFile("copy.csv", GOOD_BILL));
    expect(duplicate.status()).toBe(409);
    expect((await duplicate.json()).error.code).toBe("duplicate_document");

    const wrongType = await api.post("/api/documents", billFile("bill.pdf", "%PDF"));
    expect(wrongType.status()).toBe(415);

    const fakeZip = await api.post("/api/documents", billFile("bill.csv.gz", GOOD_BILL));
    expect(fakeZip.status()).toBe(415);

    const noFile = await api.post("/api/documents", { multipart: { other: "x" } });
    expect(noFile.status()).toBe(422);
  });

  await test.step("an oversized upload is refused", async () => {
    const tooBig = Buffer.alloc((UPLOAD_LIMIT_MB + 2) * 1024 * 1024, "a");
    const response = await api.post("/api/documents", billFile("huge.csv", tooBig));
    expect(response.status()).toBe(413);
  });

  await test.step("a file we cannot read fails with a reason", async () => {
    const response = await api.post("/api/documents", billFile("people.csv", NOT_A_BILL));
    expect(response.status()).toBe(201);
    const { id } = await response.json();
    await waitForStatus(api, id, "failed");
    const failed = await (await api.get(`/api/documents/${id}`)).json();
    expect(failed.error_message).toContain("do not recognise");
    expect((await api.delete(`/api/documents/${id}`)).status()).toBe(204);
  });

  await test.step("GET /api/documents and GET /api/documents/{id}", async () => {
    const list = await (await api.get("/api/documents")).json();
    expect(list.map((item: { id: string }) => item.id)).toEqual([documentId]);
    const document = await (await api.get(`/api/documents/${documentId}`)).json();
    expect(document.row_count).toBe(2);
    expect(document.provider_name).toBe("aws");
    expect(document.first_month).toBe("2026-09-01");
    expect(document.last_month).toBe("2026-10-01");
  });

  await test.step("bad document ids are handled", async () => {
    expect((await api.get(`/api/documents/${crypto.randomUUID()}`)).status()).toBe(404);
    expect((await api.get("/api/documents/not-an-id")).status()).toBe(422);
  });

  await test.step("POST /api/documents/{id}/reprocess", async () => {
    const response = await api.post(`/api/documents/${documentId}/reprocess`);
    expect(response.status()).toBe(202);
    await waitForStatus(api, documentId, "processed");
  });

  await test.step("GET /api/analytics/overview", async () => {
    const overview = await (await api.get("/api/analytics/overview?months=6")).json();
    expect(overview.currency).toBe("USD");
    expect(overview.total).toBe("250.00");
    expect(overview.latest_cost).toBe("150.00");
    expect(overview.change.percent).toBe("50.0");
    expect(overview.top_services[0].name).toBe("EC2");
    expect(overview.trend).toHaveLength(6);
  });

  await test.step("analytics filters and limits", async () => {
    const effective = await api.get("/api/analytics/overview?cost_type=effective");
    expect(effective.status()).toBe(200);
    expect(await (await api.get("/api/analytics/overview?provider=azure")).json()).toBeNull();
    expect((await api.get("/api/analytics/overview?months=0")).status()).toBe(422);
    expect((await api.get("/api/analytics/overview?months=37")).status()).toBe(422);
    expect((await api.get("/api/analytics/overview?cost_type=wrong")).status()).toBe(422);
  });

  await test.step("GET /api/analytics/compare", async () => {
    const rows = await (
      await api.get("/api/analytics/compare?first=2026-09-01&second=2026-10-01")
    ).json();
    expect(rows[0]).toMatchObject({ service: "EC2", difference: "50.00", percent: "50.0" });
    expect((await api.get("/api/analytics/compare")).status()).toBe(422);
    expect((await api.get("/api/analytics/compare?first=nope&second=nope")).status()).toBe(422);
  });

  await test.step("GET /api/analytics/unusual", async () => {
    expect(await (await api.get("/api/analytics/unusual")).json()).toEqual([]);
  });

  await test.step("DELETE /api/documents/{id} also clears the analytics", async () => {
    expect((await api.delete(`/api/documents/${documentId}`)).status()).toBe(204);
    expect(await (await api.get("/api/analytics/overview")).json()).toBeNull();
    expect((await api.delete(`/api/documents/${documentId}`)).status()).toBe(404);
  });

  await test.step("POST /api/documents/sample gives the design's figures", async () => {
    const response = await api.post("/api/documents/sample");
    expect(response.status()).toBe(201);
    await waitForStatus(api, (await response.json()).id, "processed");
    const overview = await (await api.get("/api/analytics/overview")).json();
    expect(overview.total).toBe("1245.60");
    expect(overview.change.percent).toBe("-8.1");
    expect((await api.post("/api/documents/sample")).status()).toBe(409);
  });

  await test.step("POST /api/auth/logout ends the session", async () => {
    const response = await api.post("/api/auth/logout");
    expect(response.status()).toBe(200);
    expect((await response.json()).logout_url).toContain("/logout");
    expect((await api.get("/api/me")).status()).toBe(401);
  });
});
