import type { NextConfig } from "next";

const isDev = process.env.NODE_ENV !== "production";

const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const ws = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
const storage = "http://localhost:9000";

// CSP (PLAN 9.6): connect to the API, its WebSocket and MinIO (presigned POST), frame MinIO for the PDF viewer.
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  `img-src 'self' data: blob: ${storage} ${api}`,
  "font-src 'self' data:",
  `connect-src 'self' ${api} ${ws} ${storage}${isDev ? " ws://localhost:3000" : ""}`,
  `frame-src ${storage} blob:`,
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
].join("; ");

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Content-Security-Policy", value: csp },
        ],
      },
    ];
  },
};

export default nextConfig;
