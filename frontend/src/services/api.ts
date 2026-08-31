import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

/**
 * Normalized shape all API errors are converted to before being rejected,
 * so callers never have to branch on Axios-specific error internals.
 */
export interface ApiError {
  message: string;
  status?: number;
  requestUrl?: string;
}

/**
 * Shared Axios client for all backend requests.
 *
 * There is no authentication in this MVP (see CLAUDE.md / INITIAL.md), so
 * no token-injection logic lives here. The interceptors only tag requests
 * for traceability and normalize failures into `ApiError`.
 */
// Falls back to a relative "/api/v1" (proxied by nginx — see frontend/nginx.conf)
// if VITE_API_URL wasn't baked into the build, rather than silently producing
// a broken "undefined/api/v1" base URL.
const apiOrigin = import.meta.env.VITE_API_URL || "";

const api = axios.create({
  baseURL: `${apiOrigin}/api/v1`,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => config,
  (error: AxiosError) => Promise.reject(toApiError(error)),
);

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => Promise.reject(toApiError(error)),
);

/** Convert an unknown Axios failure into a stable, UI-friendly `ApiError`. */
function toApiError(error: AxiosError): ApiError {
  const responseData = error.response?.data as { detail?: string; message?: string } | undefined;

  return {
    message: responseData?.detail ?? responseData?.message ?? error.message ?? "An unexpected error occurred.",
    status: error.response?.status,
    requestUrl: error.config?.url,
  };
}

/**
 * Build a full URL for a media asset (e.g. a clip thumbnail) whose path was
 * stored relative to the backend's storage root. Backed by the `/media`
 * static-files mount in `app/main.py`, distinct from the API's `/api/v1`
 * base and from the dedicated streamed `/clips/{id}/download` endpoint.
 */
export function getMediaUrl(relativePath: string): string {
  return `${apiOrigin}/media/${relativePath}`;
}

export default api;
