import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@sirat/api-client", "@sirat/shared-types", "@sirat/ui"]
};

export default nextConfig;
