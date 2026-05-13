'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { startGmailSync, getGmailSyncStatus } from '@/lib/api/gmail-service';
import type { GmailSyncState, GmailSyncStatus } from '@/lib/types';

const STORAGE_KEY = 'flighttrackr_gmail_sync';
const POLL_INTERVAL_MS = 2000;

function mapBackendStatus(
  backendStatus: string,
  passesFound: number,
): GmailSyncStatus {
  switch (backendStatus) {
    case 'pending':  return 'connecting';
    case 'running':  return passesFound > 0 ? 'parsing' : 'scanning';
    case 'completed': return 'synced';
    case 'failed':   return 'error';
    default:         return 'idle';
  }
}

export function useGmailSync() {
  const [syncState, setSyncState] = useState<GmailSyncState>({
    status: 'idle',
    lastSyncedAt: null,
    emailsScanned: 0,
    boardingPassesFound: 0,
    error: null,
  });
  const [isFirstSync, setIsFirstSync] = useState(false);
  const [initialized, setInitialized] = useState(false);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current !== null) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  // Hydrate from localStorage on mount
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        setSyncState(JSON.parse(stored) as GmailSyncState);
      } catch {
        localStorage.removeItem(STORAGE_KEY);
        setIsFirstSync(true);
      }
    } else {
      setIsFirstSync(true);
    }
    setInitialized(true);
  }, []);

  // Clean up interval on unmount
  useEffect(() => () => stopPolling(), [stopPolling]);

  const startSync = useCallback(() => {
    // Prevent double-trigger while already running
    if (
      syncState.status === 'connecting' ||
      syncState.status === 'scanning' ||
      syncState.status === 'parsing'
    ) {
      return () => {};
    }

    setSyncState(prev => ({ ...prev, status: 'connecting', error: null }));

    let cancelled = false;

    startGmailSync()
      .then(job => {
        if (cancelled) return;

        setSyncState(prev => ({ ...prev, jobId: job.job_id }));

        // Begin polling for status updates
        pollRef.current = setInterval(async () => {
          if (cancelled) { stopPolling(); return; }

          try {
            const res = await getGmailSyncStatus();
            if (cancelled) return;

            const frontendStatus = mapBackendStatus(res.status, res.passes_found);

            setSyncState(prev => ({
              ...prev,
              status: frontendStatus,
              emailsScanned: res.emails_scanned,
              boardingPassesFound: res.passes_found,
              error: res.error ?? null,
              lastSyncedAt: res.status === 'completed'
                ? (res.last_synced_at ?? new Date().toISOString())
                : prev.lastSyncedAt,
            }));

            if (res.status === 'completed') {
              stopPolling();
              const finalState: GmailSyncState = {
                status: 'synced',
                emailsScanned: res.emails_scanned,
                boardingPassesFound: res.passes_found,
                lastSyncedAt: res.last_synced_at ?? new Date().toISOString(),
                error: null,
              };
              if (typeof window !== 'undefined') {
                localStorage.setItem(STORAGE_KEY, JSON.stringify(finalState));
              }
              setIsFirstSync(false);
            } else if (res.status === 'failed') {
              stopPolling();
            }
          } catch {
            // Network hiccup — keep polling; don't fail the sync
          }
        }, POLL_INTERVAL_MS);
      })
      .catch(err => {
        if (cancelled) return;
        setSyncState(prev => ({
          ...prev,
          status: 'error',
          error: err instanceof Error ? err.message : 'Failed to start sync',
        }));
      });

    // Return cleanup so callers can cancel on unmount
    return () => {
      cancelled = true;
      stopPolling();
    };
  }, [syncState.status, stopPolling]);

  const resetSync = useCallback(() => {
    stopPolling();
    if (typeof window !== 'undefined') {
      localStorage.removeItem(STORAGE_KEY);
    }
    setSyncState({
      status: 'idle',
      lastSyncedAt: null,
      emailsScanned: 0,
      boardingPassesFound: 0,
      error: null,
    });
    setIsFirstSync(true);
  }, [stopPolling]);

  return { syncState, isFirstSync, initialized, startSync, resetSync };
}
