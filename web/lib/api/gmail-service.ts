import httpClient from './http-client'

export interface GmailSyncStatusResponse {
  status: 'pending' | 'running' | 'completed' | 'failed' | 'idle'
  emails_scanned: number
  passes_found: number
  passes_saved: number
  last_synced_at: string | null
  error: string | null
}

export async function getGmailSyncStatus(): Promise<GmailSyncStatusResponse> {
  return httpClient.get<GmailSyncStatusResponse>('/gmail/sync/status')
}
