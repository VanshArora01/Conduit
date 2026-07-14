import type { NextConfig } from "next";

const BACKEND_URL =
  process.env.BACKEND_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // Proxy /api/v1 → FastAPI so the browser always uses same-origin fetches.
  // Avoids CORS / Failed to fetch when localhost vs 127.0.0.1 / IPv6 mismatch.
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${BACKEND_URL}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
