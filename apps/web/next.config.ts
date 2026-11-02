import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  // In production Caddy sends /api to FastAPI. This covers local use.
  async rewrites() {
    const apiUrl = process.env.API_INTERNAL_URL;
    if (!apiUrl) {
      throw new Error("API_INTERNAL_URL is not set. See .env.example.");
    }
    return [{ source: "/api/:path*", destination: `${apiUrl}/api/:path*` }];
  },
};

export default nextConfig;
