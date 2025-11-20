export const API_BASE_URL: string = import.meta.env?.VITE_API_BASE_URL ?? '/api';
export const AUTH_TOKEN_KEY: string = import.meta.env?.VITE_AUTH_TOKEN_KEY ?? 'JANUS_AUTH_TOKEN';
const env: any = (import.meta as any).env || {}
export const FEATURE_SSE: boolean = (env.VITE_FEATURE_SSE ?? 'true') === 'true';
export const UX_METRICS_SAMPLING: number = Number(env.VITE_UX_METRICS_SAMPLING ?? '0.3');
export const SSE_RETRY_MAX_SECONDS: number = Number(env.VITE_SSE_RETRY_MAX_SECONDS ?? '30');