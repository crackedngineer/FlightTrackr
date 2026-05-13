import httpClient from './http-client'

export interface GmailSyncJob {
  job_id: string
  task_id: string | null
  status: string
}

export interface GmailSyncStatusResponse {
  status: 'pending' | 'running' | 'completed' | 'failed' | 'idle'
  emails_scanned: number
  passes_found: number
  passes_saved: number
  last_synced_at: string | null
  error: string | null
}

export async function startGmailSync(): Promise<GmailSyncJob> {
  return httpClient.post<GmailSyncJob>('/gmail/sync', {})
}

export async function getGmailSyncStatus(): Promise<GmailSyncStatusResponse> {
  return httpClient.get<GmailSyncStatusResponse>('/gmail/sync/status')
}
