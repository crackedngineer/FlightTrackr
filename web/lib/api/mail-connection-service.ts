import httpClient from './http-client';
import type { MailConnection, ConnectMailResponse, MailCallbackResult } from '@/lib/types';

export async function listMailConnections(): Promise<MailConnection[]> {
  return httpClient.get<MailConnection[]>('/mail/connections');
}

export async function connectMailProvider(provider: string): Promise<ConnectMailResponse> {
  return httpClient.post<ConnectMailResponse>(`/mail/${provider}/connect`, {});
}

export async function exchangeMailCode(
  provider: string,
  code: string,
  state: string,
): Promise<MailCallbackResult> {
  return httpClient.post<MailCallbackResult>(`/mail/${provider}/callback`, { code, state });
}

export async function revokeMailConnection(connectionId: string): Promise<void> {
  return httpClient.delete(`/mail/connections/${connectionId}`);
}
