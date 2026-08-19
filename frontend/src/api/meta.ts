import { apiFetch } from './client'

// docs/api-contracts/meta.md — GET /meta/deploy-info (DRAFT, 백엔드 미구현).
export interface DeployInfo {
  apiVersion: string
  serverIp: string
  serverName: string
  clientIp: string
  xForwardedFor: string | null
}

export function fetchDeployInfo(): Promise<DeployInfo> {
  return apiFetch<DeployInfo>('/meta/deploy-info')
}
