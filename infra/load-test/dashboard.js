// Load test for the dashboard routes. Run with `make load-test`.
// Many signed-in users open Overview, Documents and Analytics at the same time.
// AI questions are left out on purpose: they would use up the free Gemini quota in seconds.
import http from "k6/http";
import { check, group, sleep } from "k6";

const BASE = __ENV.API_URL;
const COOKIE = `${__ENV.COOKIE_NAME}=${__ENV.SESSION_COOKIE}`;
const params = { headers: { Cookie: COOKIE } };

export const options = {
  scenarios: {
    dashboard: {
      executor: "ramping-vus",
      stages: [
        { duration: "30s", target: Number(__ENV.PEAK_USERS || 25) },
        { duration: "1m", target: Number(__ENV.PEAK_USERS || 25) },
        { duration: "15s", target: 0 },
      ],
    },
  },
  // The test fails if these are broken.
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<500"],
  },
};

export function setup() {
  const me = http.get(`${BASE}/api/me`, params);
  if (me.status !== 200) {
    throw new Error(`The session cookie was refused (${me.status}). Run make load-test again.`);
  }
}

export default function () {
  group("Overview page", () => {
    const responses = http.batch([
      ["GET", `${BASE}/api/me`, null, params],
      ["GET", `${BASE}/api/analytics/overview?months=6`, null, params],
      ["GET", `${BASE}/api/recommendations`, null, params],
      ["GET", `${BASE}/api/documents`, null, params],
    ]);
    responses.forEach((response) => check(response, { "status is 200": (r) => r.status === 200 }));
  });
  sleep(1);

  group("Analytics page", () => {
    const responses = http.batch([
      ["GET", `${BASE}/api/analytics/overview?months=12`, null, params],
      ["GET", `${BASE}/api/analytics/unusual`, null, params],
      ["GET", `${BASE}/api/analytics/compare?first=2026-09-01&second=2026-10-01`, null, params],
    ]);
    responses.forEach((response) => check(response, { "status is 200": (r) => r.status === 200 }));
  });
  sleep(1);
}
