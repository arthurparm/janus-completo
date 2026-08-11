import assert from 'node:assert/strict'
import { createServer, get } from 'node:http'
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

const serverPath = fileURLToPath(new URL('./server.mjs', import.meta.url))

function listen(server, port = 0) {
  return new Promise((resolve, reject) => {
    server.once('error', reject)
    server.listen(port, '127.0.0.1', () => {
      server.removeListener('error', reject)
      resolve(server.address().port)
    })
  })
}

function close(server) {
  server.closeAllConnections?.()
  return new Promise(resolve => server.close(resolve))
}

async function reservePort() {
  const server = createServer()
  const port = await listen(server)
  await close(server)
  return port
}

function waitForProxy(child) {
  return new Promise((resolve, reject) => {
    let stderr = ''
    const timer = setTimeout(() => {
      reject(new Error(`Frontend proxy did not start. stderr=${stderr}`))
    }, 5_000)

    child.stderr.on('data', chunk => {
      stderr += chunk.toString()
    })
    child.once('exit', code => {
      clearTimeout(timer)
      reject(new Error(`Frontend proxy exited before startup with code ${code}. stderr=${stderr}`))
    })
    child.stdout.on('data', chunk => {
      if (chunk.toString().includes('Janus frontend listening')) {
        clearTimeout(timer)
        resolve()
      }
    })
  })
}

function fetchText(url) {
  return new Promise((resolve, reject) => {
    const request = get(url, response => {
      let body = ''
      response.setEncoding('utf8')
      response.on('data', chunk => {
        body += chunk
      })
      response.on('end', () => {
        resolve({ status: response.statusCode, body })
      })
    })
    request.once('error', reject)
  })
}

test('routes private and public API prefixes to their dedicated upstreams', async t => {
  const privateRequests = []
  const publicRequests = []
  const privateBackend = createServer((request, response) => {
    privateRequests.push(request.url)
    response.writeHead(200, { 'Content-Type': 'text/plain' })
    response.end('private')
  })
  const publicBackend = createServer((request, response) => {
    publicRequests.push(request.url)
    response.writeHead(200, { 'Content-Type': 'application/json' })
    response.end('{"issuer":"https://idp.example"}')
  })
  const privatePort = await listen(privateBackend)
  const publicPort = await listen(publicBackend)
  const proxyPort = await reservePort()
  const proxy = spawn(process.execPath, [serverPath], {
    env: {
      ...process.env,
      JANUS_API_URL: `http://127.0.0.1:${privatePort}`,
      JANUS_PUBLIC_API_URL: `http://127.0.0.1:${publicPort}`,
      PORT: String(proxyPort),
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  })

  t.after(async () => {
    proxy.kill()
    await close(privateBackend)
    await close(publicBackend)
  })

  await waitForProxy(proxy)
  const privateResponse = await fetchText(
    `http://127.0.0.1:${proxyPort}/api/v1/users/me?expanded=true`,
  )
  const publicResponse = await fetchText(
    `http://127.0.0.1:${proxyPort}/public-api/api/v1/auth/oidc-config`,
  )
  const healthResponse = await fetchText(
    `http://127.0.0.1:${proxyPort}/healthz/user`,
  )

  assert.deepEqual(privateResponse, { status: 200, body: 'private' })
  assert.deepEqual(publicResponse, {
    status: 200,
    body: '{"issuer":"https://idp.example"}',
  })
  assert.deepEqual(healthResponse, { status: 200, body: 'private' })
  assert.deepEqual(privateRequests, ['/api/v1/users/me?expanded=true', '/healthz/user'])
  assert.deepEqual(publicRequests, ['/api/v1/auth/oidc-config'])
})

test('closes the upstream response when the client abandons a proxied stream', async t => {
  let resolveUpstreamClosed
  const upstreamClosed = new Promise(resolve => {
    resolveUpstreamClosed = resolve
  })

  const backend = createServer((_request, response) => {
    response.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
    })
    const timer = setInterval(() => response.write('event: heartbeat\ndata: {}\n\n'), 20)
    response.once('close', () => {
      clearInterval(timer)
      resolveUpstreamClosed()
    })
  })
  const backendPort = await listen(backend)
  const proxyPort = await reservePort()
  const proxy = spawn(process.execPath, [serverPath], {
    env: {
      ...process.env,
      JANUS_API_URL: `http://127.0.0.1:${backendPort}`,
      PORT: String(proxyPort),
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  })

  t.after(async () => {
    proxy.kill()
    await close(backend)
  })

  await waitForProxy(proxy)
  await new Promise((resolve, reject) => {
    const request = get(`http://127.0.0.1:${proxyPort}/api/slow-stream`, response => {
      response.once('data', () => {
        response.destroy()
        resolve()
      })
    })
    request.once('error', reject)
  })

  const closedInTime = await Promise.race([
    upstreamClosed.then(() => true),
    new Promise(resolve => setTimeout(() => resolve(false), 1_000)),
  ])
  assert.equal(closedInTime, true, 'upstream stream remained active after client disconnect')
})
