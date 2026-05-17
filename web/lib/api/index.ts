/**
 * API Services barrel export.
 * Provides a single entry point for all API services.
 */

export { default as httpClient } from './http-client';
export { default as authService } from './auth-service';
export { default as boardingPassService } from './boarding-pass-service';
export { default as healthService } from './health-service';

// Export classes for type usage
export { AuthService } from './auth-service';

// Named auth functions
export { signInWithGoogle, signOut, connectGoogle, getMe } from './auth-service';

// Flight functions
export { listBookings, getBooking } from './flight-service';

// Gmail sync functions
export { getGmailSyncStatus } from './gmail-service';
export type { GmailSyncStatusResponse } from './gmail-service';

// Mail connection functions
export {
  listMailConnections,
  connectMailProvider,
  exchangeMailCode,
  revokeMailConnection,
} from './mail-connection-service';

export { BoardingPassService } from './boarding-pass-service';
export { HealthService } from './health-service';