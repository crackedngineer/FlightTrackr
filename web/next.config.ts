import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Required for the production Docker image (copies only the minimal server bundle)
  output: "standalone",
  allowedDevOrigins: ["flighttrackr.tailcda03.ts.net"],
};

export default nextConfig;
