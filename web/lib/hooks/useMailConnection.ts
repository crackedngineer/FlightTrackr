'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  listMailConnections,
  connectMailProvider,
  revokeMailConnection,
} from '@/lib/api/mail-connection-service';
import type { MailConnection, MailConnectionState } from '@/lib/types';

interface UseMailConnectionReturn {
  connections: MailConnection[];
  connectionState: MailConnectionState;
  isLoading: boolean;
  error: string | null;
  startConnect: (provider: string) => Promise<void>;
  revoke: (connectionId: string) => Promise<void>;
  refetch: () => Promise<void>;
  isProviderConnected: (provider: string) => boolean;
}

export function useMailConnection(): UseMailConnectionReturn {
  const [connections, setConnections] = useState<MailConnection[]>([]);
  const [connectionState, setConnectionState] = useState<MailConnectionState>('disconnected');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await listMailConnections();
      setConnections(data);
      setConnectionState(
        data.some((c) => c.status === 'active') ? 'connected' : 'disconnected',
      );
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load connections');
      setConnectionState('error');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  const startConnect = useCallback(async (provider: string) => {
    setConnectionState('connecting');
    setError(null);
    try {
      const { auth_url } = await connectMailProvider(provider);
      window.location.href = auth_url;
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to initiate connection');
      setConnectionState('error');
    }
  }, []);

  const revoke = useCallback(
    async (connectionId: string) => {
      await revokeMailConnection(connectionId);
      await refetch();
    },
    [refetch],
  );

  const isProviderConnected = useCallback(
    (provider: string) =>
      connections.some((c) => c.provider === provider && c.status === 'active'),
    [connections],
  );

  return {
    connections,
    connectionState,
    isLoading,
    error,
    startConnect,
    revoke,
    refetch,
    isProviderConnected,
  };
}
