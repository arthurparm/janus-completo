import { createReadStream, existsSync, statSync } from 'node:fs';
import { createServer, request as httpRequest } from 'node:http';
import { request as httpsRequest } from 'node:https';
import { extname, join, normalize, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const staticRoot = resolve(__dirname, 'dist/janus-angular/browser');
const backendUrl = new URL(process.env.JANUS_API_URL || 'http://janus-api:8000');
const publicBackendUrl = new URL(
  process.env.JANUS_PUBLIC_API_URL || 'http://janus-public-api:8000',
);
const port = Number(process.env.PORT || 4300);

const contentTypes = new Map([
  ['.css', 'text/css; charset=utf-8'],
  ['.html', 'text/html; charset=utf-8'],
  ['.ico', 'image/x-icon'],
  ['.js', 'text/javascript; charset=utf-8'],
  ['.json', 'application/json; charset=utf-8'],
  ['.map', 'application/json; charset=utf-8'],
  ['.png', 'image/png'],
  ['.svg', 'image/svg+xml'],
  ['.txt', 'text/plain; charset=utf-8'],
  ['.webmanifest', 'application/manifest+json; charset=utf-8'],
  ['.woff2', 'font/woff2'],
]);

function resolveProxyTarget(pathname) {
  if (pathname === '/public-api' || pathname.startsWith('/public-api/')) {
    return { backendUrl: publicBackendUrl, stripPrefix: '/public-api' };
  }
  if (pathname === '/api' || pathname.startsWith('/api/') || pathname === '/healthz') {
    return { backendUrl, stripPrefix: '' };
  }
  return null;
}

function sendStatic(response, pathname) {
  const decodedPath = decodeURIComponent(pathname.split('?')[0] || '/');
  const relativePath = normalize(decodedPath).replace(/^(\.\.[/\\])+/, '');
  let candidate = resolve(staticRoot, `.${relativePath}`);
  if (!candidate.startsWith(staticRoot)) {
    response.writeHead(403);
    response.end('Forbidden');
    return;
  }

  if (!existsSync(candidate) || statSync(candidate).isDirectory()) {
    candidate = join(staticRoot, 'index.html');
  }

  const type = contentTypes.get(extname(candidate)) || 'application/octet-stream';
  response.writeHead(200, { 'Content-Type': type });
  createReadStream(candidate).pipe(response);
}

function proxyRequest(clientRequest, clientResponse, proxyTarget) {
  const incoming = new URL(clientRequest.url || '/', 'http://frontend.local');
  const upstreamPath = proxyTarget.stripPrefix
    ? incoming.pathname.slice(proxyTarget.stripPrefix.length) || '/'
    : incoming.pathname;
  const target = new URL(`${upstreamPath}${incoming.search}`, proxyTarget.backendUrl);
  const headers = { ...clientRequest.headers, host: proxyTarget.backendUrl.host };
  const requestImpl = target.protocol === 'https:' ? httpsRequest : httpRequest;
  const proxy = requestImpl(
    {
      protocol: target.protocol,
      hostname: target.hostname,
      port: target.port || (target.protocol === 'https:' ? 443 : 80),
      method: clientRequest.method,
      path: `${target.pathname}${target.search}`,
      headers,
    },
    backendResponse => {
      clientResponse.writeHead(backendResponse.statusCode || 502, backendResponse.headers);
      backendResponse.pipe(clientResponse);
    },
  );

  proxy.on('error', error => {
    clientResponse.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
    clientResponse.end(JSON.stringify({ detail: 'Frontend proxy failed', error: error.message }));
  });

  clientRequest.pipe(proxy);
}

createServer((request, response) => {
  const url = new URL(request.url || '/', `http://${request.headers.host || 'localhost'}`);
  const proxyTarget = resolveProxyTarget(url.pathname);
  if (proxyTarget) {
    proxyRequest(request, response, proxyTarget);
    return;
  }
  sendStatic(response, url.pathname);
}).listen(port, '0.0.0.0', () => {
  console.log(
    `Janus frontend listening on :${port}; ` +
      `private proxy ${backendUrl.origin}; public proxy ${publicBackendUrl.origin}`,
  );
});
