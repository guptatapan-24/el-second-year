/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_BACKEND_API: process.env.NEXT_PUBLIC_BACKEND_API || 'http://localhost:8001',
    NEXT_PUBLIC_ORACLE_ADDRESS: process.env.NEXT_PUBLIC_ORACLE_ADDRESS || '',
    NEXT_PUBLIC_ETH_RPC_URL: process.env.NEXT_PUBLIC_ETH_RPC_URL || '',
  },
}

module.exports = nextConfig
