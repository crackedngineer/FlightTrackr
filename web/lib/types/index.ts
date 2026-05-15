export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonObject | JsonValue[];
export interface JsonObject {
  [key: string]: JsonValue;
}

// API Response Types
export interface ApiResponse<T = unknown> {
  success: boolean;
  message: string;
  data?: T;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    type: string;
    details?: JsonValue[];
  };
}

export class ApiClientError extends Error {
  public readonly statusCode: number;
  public readonly status: number;
  public readonly code: string;
  public readonly details?: unknown;

  constructor(message: string, statusCode = 500, code = 'API_ERROR', details?: unknown) {
    super(message);
    this.name = 'ApiClientError';
    this.statusCode = statusCode;
    this.status = statusCode;
    this.code = code;
    this.details = details;
  }

  get isNetworkError(): boolean { return this.status === 0; }
  get isClientError(): boolean  { return this.status >= 400 && this.status < 500; }
  get isServerError(): boolean  { return this.status >= 500; }
}

// Authentication Types
export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user: User;
  expires_in: number;
}

export interface User {
  id: string;
  email: string;
  name?: string;
  user_metadata: Record<string, JsonValue>;
  app_metadata: Record<string, JsonValue>;
}

export interface TokenRefreshRequest {
  refresh_token: string;
}

// Boarding Pass Types
export interface BoardingPassData {
  passenger_name: string | null;
  flight_number: string | null;
  departure_airport: string | null;
  arrival_airport: string | null;
  departure_date: string | null;
  seat_number: string | null;
  gate: string | null;
  terminal: string | null;
  operator_code: string | null;
  class_of_service: string | null;
}

export interface UploadResponse {
  success: boolean;
  message: string;
  data: BoardingPassData | null;
}

export interface SupportedAirline {
  name: string;
  code: string;
  country: string;
  supported_features: string[];
}

export interface SupportedAirlinesResponse {
  supported_airlines: SupportedAirline[];
  total_supported: number;
  generic_parser: {
    available: boolean;
    description: string;
  };
}

// Health Check Types
export interface HealthResponse {
  status: string;
  message: string;
  timestamp?: string;
}

export interface ReadinessResponse {
  status: string;
  services: Record<string, JsonValue>;
}

// Form Types
export interface LoginFormData {
  provider: 'google';
}

export interface FileUploadFormData {
  file: File;
}

// UI State Types
export interface LoadingState {
  isLoading: boolean;
  error?: string | null;
}

export interface AuthState extends LoadingState {
  user?: User | null;
  isAuthenticated: boolean;
  accessToken?: string | null;
  refreshToken?: string | null;
}

export interface BoardingPassState extends LoadingState {
  currentBoardingPass?: BoardingPassData | null;
  supportedAirlines: SupportedAirline[];
}

export interface RequestConfig {
  timeout?: number;
  retries?: number;
  includeAuth?: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}

// ─── Flight Types ──────────────────────────────────────────

export type FlightStatus = 'upcoming' | 'completed' | 'cancelled';
export type FlightSource = 'gmail' | 'manual';

export interface BookingGroup {
  pnr: string;
  legs: Flight[];
  isConnecting: boolean;
}

export interface Flight {
  id: string;
  flight_number: string;
  airline: string;
  airline_code: string;
  passenger_name?: string;
  departure_airport: string;
  departure_city: string;
  arrival_airport: string;
  arrival_city: string;
  departure_time: string;
  arrival_time: string;
  date: string;
  seat: string | null;
  pnr: string | null;
  gate: string | null;
  terminal: string | null;
  class_of_service: string | null;
  status: FlightStatus;
  duration: string | null;
  source: FlightSource;
  parsed_at: string;
}

// ─── Gmail Sync Types ──────────────────────────────────────

export type GmailSyncStatus =
  | 'idle'
  | 'connecting'
  | 'scanning'
  | 'parsing'
  | 'synced'
  | 'error';

export interface GmailSyncState {
  status: GmailSyncStatus;
  lastSyncedAt: string | null;
  emailsScanned: number;
  boardingPassesFound: number;
  error: string | null;
  jobId?: string;
}

// ─── Mail Connection Types ────────────────────────────────────────────────────

export interface MailConnection {
  id: string;
  provider: string;
  provider_email: string;
  status: 'active' | 'revoked' | 'error';
  scopes: string[];
  connected_at: string | null;
  last_synced_at: string | null;
}

export type MailConnectionState =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'error';

export interface ConnectMailResponse {
  auth_url: string;
  state: string;
}

export interface MailCallbackResult {
  message: string;
  connection_id: string;
  sync_triggered: boolean;
}
