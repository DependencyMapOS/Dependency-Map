import path from "path";
import type { NextConfig } from "next";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  // Monorepo: trace files from repo root when parent lockfiles exist
  outputFileTracingRoot: path.join(__dirname, ".."),
};

export default nextConfig;
