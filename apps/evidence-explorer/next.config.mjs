import { fileURLToPath } from "node:url";

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  reactStrictMode: true,
  trailingSlash: true,
  // Keep Turbopack bounded to this app instead of resolving an unrelated lockfile above the workspace.
  turbopack: { root: fileURLToPath(new URL(".", import.meta.url)) },
  // This research app already has project instructions; avoid generated agent-rule files at runtime.
  agentRules: false,
};

export default nextConfig;
