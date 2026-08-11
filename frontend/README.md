# Janus Angular — Frontend

This directory contains the Angular frontend for the Janus AI system.

**For full documentation and backlog, please refer to the [root README](../README.md).**

## Quick Start

### Prerequisites
- Node.js 20

### Setup

```bash
# Ensure you are in the frontend/ directory
npm install
npm start
```

The application will be available at `http://localhost:4200/`.
The development proxy forwards private `/api` requests to `http://localhost:8000`
and strips `/public-api` before forwarding public authentication discovery to
`http://localhost:8001`.

In Docker (compose PC1), the frontend runs at `http://localhost:4300/`. Its
runtime server routes `/api` to `JANUS_API_URL` (`janus-api` by default) and
`/public-api` to `JANUS_PUBLIC_API_URL` (`janus-public-api` by default), keeping
the browser on the same origin while preserving the public/private API boundary.
