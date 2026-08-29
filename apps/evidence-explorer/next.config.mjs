import { fileURLToPath } from "node:url";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  trailingSlash: true,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()" },
          { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
        ],
      },
      {
        source: "/api/research-chat",
        headers: [
          { key: "Cache-Control", value: "no-store, max-age=0" },
          { key: "Content-Security-Policy", value: "default-src 'none'; frame-ancestors 'none'; sandbox" },
        ],
      },
    ];
  },
  // Retain a bounded Turbopack root for optional experiments. Production and local
  // development use webpack because Turbopack 16.3.1 emitted Cesium's embedded
  // WebAssembly bytes as invalid octal escapes inside a template string.
  turbopack: { root: fileURLToPath(new URL(".", import.meta.url)) },
  // This research app already has project instructions; avoid generated agent-rule files at runtime.
  agentRules: false,
};

export default nextConfig;
