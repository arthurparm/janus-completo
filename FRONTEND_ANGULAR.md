# Frontend Angular

## 1. Angular Architecture

The frontend uses Angular 20 with a fully standalone component architecture. All components, directives, and pipes use the `standalone: true` flag and are imported directly rather than through NgModules. The application bootstrap is `bootstrapApplication(App)` in [main.ts](file:///h:/repos/janus-completo/frontend/src/main.ts).

**Signals**: Reactive state management uses Angular Signals (`signal()`, `computed()`, `effect()`) for fine-grained reactivity. Components use `ChangeDetectionStrategy.OnPush` with signal-based change detection. Examples include `ChatStreamService.status$` converted to BehaviorSubject for RxJS interop, and `AuthService._isAuthenticated` as a private signal exposed as a readonly `isAuthenticated()` computed.

**Zoneless Change Detection**: Configured via `provideZonelessChangeDetection()` in the app providers. This eliminates zone.js overhead and uses Angular 20's built-in signal-based change detection. Tests use `provideZonelessChangeDetection()` in TestBed configuration.

**esbuild Builder**: The Angular build uses `@angular/build:application` builder (esbuild-based) for both development and production builds. Configuration in [angular.json](file:///h:/repos/janus-completo/frontend/angular.json) shows the application builder with SCSS inline style language and service worker support.

**Lazy-Loaded Routes**: The [app.routes.ts](file:///h:/repos/janus-completo/frontend/src/app/app.routes.ts) defines lazy-loaded feature routes using the `loadComponent` pattern:

```
/ (home) -> Home component
/login -> LoginComponent
/register -> RegisterComponent
/conversations/:conversationId -> ConversationsComponent
/observability -> ObservabilityComponent
/tools -> ToolsComponent
/admin -> admin routes (autonomy, backlog, code-qa)
```

## 2. Auth System

**JWT Local Auth**: The [AuthService](file:///h:/repos/janus-completo/frontend/src/app/core/auth/auth.service.ts) (425 lines) manages JWT-based local authentication. It stores the access token and refresh token in both localStorage (persistent sessions) and sessionStorage (ephemeral sessions), chosen based on a "remember me" flag.

**Session Restoration**: On app initialization, `restoreSession()` checks for existing tokens. If found, it validates the session by calling `GET /v1/auth/me`. If the token is expired (401), it attempts a refresh via `POST /v1/auth/local/refresh`. If both fail, the session is cleared. The `refreshAccessToken()` method uses a promise lock (`refreshPromise`) to prevent concurrent refresh calls.

**Auth Signals**: `_isAuthenticated` (signal), `_user` (signal for User object), `_authReady` (signal for initialization completion), `_authRateLimitUntilMs` (signal for rate limit cooldown). Exposed as readonly computed signals for template binding.

**5 Guards**: Defined in [guards/*.ts](file:///h:/repos/janus-completo/frontend/src/app/core/guards/):
- `AuthGuard` (canActivate/canActivateChild/canLoad): Checks authentication with timeout (10s). Redirects to /login.
- `RoleGuard`: Checks if user has required roles.
- `PermissionGuard`: Checks specific permissions.
- `NoAuthGuard`: Prevents authenticated users from accessing login/register pages.
- `SystemReadyGuard`: Waits for system initialization before allowing access.

**Interceptor Chain**: 5 functional interceptors in [core/interceptors/](file:///h:/repos/janus-completo/frontend/src/app/core/interceptors/):
- `base-url.interceptor.ts`: Prepends API_BASE_URL to all requests
- `auth.interceptor.ts`: Attaches JWT Bearer token to all API requests
- `auth-session.interceptor.ts` (89 lines): Handles 401 responses by attempting token refresh. If refresh succeeds, retries the original request with the new token. If refresh fails, redirects to /login. Also captures 429 rate limits and blocks subsequent requests until cooldown expires.
- `error-logger.interceptor.ts`: Logs all HTTP errors to the logging service
- `error-mapping.interceptor.ts`: Maps backend error responses to user-friendly messages. Enables offline mode when the backend is unreachable.

**Token Storage**: [auth.utils.ts](file:///h:/repos/janus-completo/frontend/src/app/services/auth.utils.ts) provides `getStoredAuthToken()`, `storeAuthToken()`, `clearStoredAuthToken()` and refresh token equivalents. Tokens are stored in both localStorage and sessionStorage with preference based on "remember me".

## 3. SSE Chat Streaming

The [ChatStreamService](file:///h:/repos/janus-completo/frontend/src/app/services/chat-stream.service.ts) (532 lines) implements Server-Sent Events streaming using the Fetch API's `ReadableStream` interface.

**7 Reactive Observables**: `status$` (StreamStatus: idle/connecting/open/streaming/retrying/closed/error), `typing$` (boolean), `partials$` ({text}), `done$` (StreamDone with conversation_id, citations, understanding, confirmation, agent_state), `errors$` (StreamError with error code, category, retryable flag, attempt number), `cognitive$` (StreamCognitiveStatus with state and confidence_band), `toolStatus$` (StreamToolStatus with tool execution events).

**Event Protocol**: The SSE stream uses named events: `start` (connection established), `protocol` (protocol version), `heartbeat` (keepalive), `ack` (message acknowledged), `cognitive_status` (thinking/streaming response), `tool_status` (tool execution progress), `partial` (text chunks), `token` (token-level streaming), `done` (final message with metadata), `error` (error with retry info).

**Exponential Backoff with Jitter**: On connection errors, the service retries with `min(SSE_RETRY_MAX_SECONDS, 2^attempt + random(0, 0.5)*1000)` milliseconds delay. Default max retries from `SSE_MAX_RETRIES` config. Max 8 retries, max 30s backoff. Non-retryable errors (401, 403, 404, 413, 422) immediately terminate the stream.

**Abort Controller**: Each stream uses an `AbortController` for clean cancellation. The `stop()` method aborts the current stream and prevents stale responses from being processed via a sequence counter (`streamSeq`).

## 4. Global State

**GlobalStateStore**: Located at [core/services/](file:///h:/repos/janus-completo/frontend/src/app/core/services/), this service manages application-wide state using Angular Signals combined with RxJS polling. It monitors system health by polling `/v1/system/status` and `/v1/workers/status` endpoints.

**System Health Monitoring**: The store periodically fetches health metrics from the backend. System status is exposed as signals (`systemStatus`, `workerStatus`) and drives the header indicator and observability dashboard widgets.

**Worker Control**: The store provides methods to start/stop specific workers via the admin API. Worker state changes are reflected in real-time through signal updates.

## 5. HTTP Interceptor Chain

5 functional interceptors execute in this order:
1. **base-url**: Prepends the API base URL to relative paths
2. **auth**: Attaches `Authorization: Bearer {token}` header from stored JWT
3. **auth-session**: Catches 401 responses, attempts refresh via AuthService, retries original request. Catches 429 responses, captures rate limit state in AuthService.
4. **error-logger**: Records all HTTP errors to AppLoggerService with context (URL, method, status, timing)
5. **error-mapping**: Maps HTTP error codes to user-friendly messages. On network failure, triggers offline mode notification.

The auth-session interceptor uses `HttpContextToken` to skip refresh for auth endpoints (login, register, refresh, reset).

## 6. WebRTC Integration

**Janus WebRTC Gateway**: The [WebRTC API service](file:///h:/repos/janus-completo/frontend/src/app/services/domain/web-rtcapi-service.ts) integrates with the Janus WebRTC gateway for real-time audio/video communication.

**Videoroom/Videocall Plugins**: Supports both videoroom (multi-party) and videocall (peer-to-peer) plugins. The service initializes the Janus JavaScript client, creates sessions, and attaches plugin handles.

**getUserMedia**: Captures local media streams via `navigator.mediaDevices.getUserMedia()`. Local and remote streams are exposed as BehaviorSubjects (`localStream$`, `remoteStream$`).

**RTCPeerConnection**: Manages WebRTC peer connections with ICE candidate negotiation. Connection state is tracked via `connectionState$` (session_ready, session_error, session_destroyed). Error handling is exposed through `webrtcErrors$`.

## 7. Observability Dashboard

**Auto-Refresh**: The [observability component](file:///h:/repos/janus-completo/frontend/src/app/features/observability/observability.ts) implements a 5-second auto-refresh interval using RxJS `interval(5000)` with `switchMap` to the API call. The interval is cancelled on component destroy.

**Queue Monitoring**: RabbitMQ queue status is displayed with details on message count, consumer count, and queue depth. The [system-status-widget](file:///h:/repos/janus-completo/frontend/src/app/features/observability/widgets/system-status-widget/system-status-widget.ts) polls `/v1/tasks/health/*` endpoints.

**System/Widget Health Status**: Each component health widget (SystemStatus, DatabaseHealth, KnowledgeHealth) displays individual status indicators (healthy/unhealthy/degraded) with drill-down details. Errors are caught gracefully with fallback display states.

## 8. Admin Autonomy Panel

**Backlog Management**: The [admin-autonomia component](file:///h:/repos/janus-completo/frontend/src/app/features/admin/autonomia/admin-autonomia.ts) (219 lines) displays the evolution backlog with columns for priority, description, status, and timestamps. Supports filtering and manual evolution triggering.

**Self-Study Control**: Provides controls for starting self-study in incremental (git diff-based) or full (entire codebase) mode. Displays study session results including reflection reports, health scores, and generated improvements.

**Code QA with Citations**: Shows code quality analysis results with citations pointing to specific files and line ranges. Uses the `AdminCodeQaResponse` model with `Citation` interface for source attribution.

## 9. Build & Deploy

**esbuild**: The `@angular/build:application` builder uses esbuild for TypeScript compilation, CSS processing, and bundling. This provides significantly faster builds than the traditional webpack-based builder.

**Proxy Configs**: Three proxy configurations for different environments:
- [proxy.conf.json](file:///h:/repos/janus-completo/frontend/proxy.conf.json): Local development (port 4200 -> 8000)
- [proxy.docker.conf.json](file:///h:/repos/janus-completo/frontend/proxy.docker.conf.json): Docker runtime (port 4300 -> janus-api:8000)
- Tailscale variant for remote access

**Docker Multi-Stage**: The [Dockerfile](file:///h:/repos/janus-completo/frontend/docker/Dockerfile) uses multi-stage build: Node.js 20 for building, nginx alpine for serving. The nginx config handles SPA routing (fallback to index.html) and reverse proxy to the backend.

**Env Vars**: Environment variables are injected at build time via Angular's `define` and at runtime via the nginx template. The frontend uses `API_BASE_URL` from `api.config.ts` which reads from `process.env` polyfill or hardcoded defaults.
