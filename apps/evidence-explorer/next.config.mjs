import { fileURLToPath } from "node:url";

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  reactStrictMode: true,
  trailingSlash: true,
  // Retain a bounded Turbopack root for optional experiments. Production and local
  // development use webpack because Turbopack 16.3.1 emitted Cesium's embedded
  // WebAssembly bytes as invalid octal escapes inside a template string.
  turbopack: { root: fileURLToPath(new URL(".", import.meta.url)) },
  // This research app already has project instructions; avoid generated agent-rule files at runtime.
  agentRules: false,
};

export default nextConfig;
