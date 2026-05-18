import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enables multi-stage Docker builds (copies only the minimal runtime)
  output: "standalone",
};

export default nextConfig;
