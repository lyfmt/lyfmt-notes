#!/usr/bin/env node

import { spawnSync } from 'node:child_process';
import { lookup } from 'node:dns/promises';
import net from 'node:net';
import tls from 'node:tls';

export const DEFAULT_API_BASE_URL = 'https://api.tavily.com';
export const DEFAULT_TIMEOUT_MS = 45_000;

export function getApiKey() {
  return (process.env.TAVILY_API_KEY ?? '').trim();
}

export function getApiBaseUrl() {
  const raw = (process.env.TAVILY_API_BASE_URL ?? DEFAULT_API_BASE_URL).trim();
  return raw.replace(/\/+$/, '');
}

export function getTimeoutMs() {
  const raw = Number.parseInt(process.env.TAVILY_TIMEOUT_MS ?? '', 10);
  if (!Number.isFinite(raw) || raw <= 0) return DEFAULT_TIMEOUT_MS;
  return raw;
}

export function envFlag(name, fallback = false) {
  const raw = (process.env[name] ?? '').trim().toLowerCase();
  if (!raw) return fallback;
  return raw === '1' || raw === 'true' || raw === 'yes' || raw === 'on';
}

export function hasCurl() {
  const result = spawnSync('curl', ['--version'], { stdio: 'ignore' });
  return result.status === 0;
}

export function buildApiUrl(path, apiBaseUrl = getApiBaseUrl()) {
  const base = apiBaseUrl.endsWith('/') ? apiBaseUrl : `${apiBaseUrl}/`;
  const cleanPath = String(path ?? '').replace(/^\/+/, '');
  return new URL(cleanPath, base).toString();
}

export function formatError(error) {
  const message = String(error?.message ?? error ?? 'Unknown error').trim();
  const codes = [error?.code, error?.cause?.code].filter(Boolean);
  const suffix = codes.length ? ` [${codes.join(', ')}]` : '';
  return `${message}${suffix}`;
}

async function requestViaFetch(url, body, timeoutMs) {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(timeoutMs),
  });

  const text = await response.text().catch(() => '');

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${text || response.statusText || 'request failed'}`);
  }

  try {
    return JSON.parse(text || 'null');
  } catch {
    throw new Error(`Invalid JSON response from Tavily: ${text.slice(0, 500)}`);
  }
}

function requestViaCurl(url, body, timeoutMs) {
  const timeoutSeconds = Math.max(1, Math.ceil(timeoutMs / 1000));
  const connectTimeoutSeconds = Math.max(5, Math.min(timeoutSeconds, 20));
  const result = spawnSync(
    'curl',
    [
      '--silent',
      '--show-error',
      '--location',
      '--max-time',
      String(timeoutSeconds),
      '--connect-timeout',
      String(connectTimeoutSeconds),
      '--write-out',
      '\n%{http_code}',
      '-H',
      'Accept: application/json',
      '-H',
      'Content-Type: application/json',
      '--data-binary',
      JSON.stringify(body),
      url,
    ],
    {
      encoding: 'utf8',
      maxBuffer: 10 * 1024 * 1024,
    }
  );

  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error((result.stderr || '').trim() || `curl exited with code ${result.status}`);
  }

  const output = result.stdout ?? '';
  const splitAt = output.lastIndexOf('\n');
  if (splitAt === -1) {
    throw new Error('curl response missing HTTP status');
  }

  const responseBody = output.slice(0, splitAt);
  const status = Number(output.slice(splitAt + 1).trim());
  if (!Number.isFinite(status)) {
    throw new Error('curl response missing valid HTTP status');
  }
  if (status < 200 || status >= 300) {
    throw new Error(`HTTP ${status}: ${responseBody.slice(0, 500)}`);
  }

  try {
    return JSON.parse(responseBody || 'null');
  } catch {
    throw new Error(`Invalid JSON response from Tavily: ${responseBody.slice(0, 500)}`);
  }
}

export async function tavilyPost(path, payload, label = 'request') {
  const apiBaseUrl = getApiBaseUrl();
  const timeoutMs = getTimeoutMs();
  const url = buildApiUrl(path, apiBaseUrl);
  const forceCurl = envFlag('TAVILY_FORCE_CURL', false);
  const attempts = [];

  if (!forceCurl) {
    try {
      return await requestViaFetch(url, payload, timeoutMs);
    } catch (error) {
      attempts.push(`fetch: ${formatError(error)}`);
    }
  }

  if (hasCurl()) {
    try {
      return requestViaCurl(url, payload, timeoutMs);
    } catch (error) {
      attempts.push(`curl: ${formatError(error)}`);
    }
  } else if (forceCurl) {
    attempts.push('curl: curl is not installed');
  }

  throw new Error(
    `Tavily ${label} failed at ${url}. ${attempts.length ? attempts.join(' | ') : 'No request method available.'}`
  );
}

export async function resolveApiHost() {
  const url = new URL(getApiBaseUrl());
  const port = Number(url.port || (url.protocol === 'https:' ? 443 : 80));
  const addresses = await lookup(url.hostname, { all: true });
  return { url, port, addresses };
}

export async function testTcpConnect(hostname, port, timeoutMs = 8_000) {
  return await new Promise((resolve) => {
    const socket = net.createConnection({ host: hostname, port });
    let settled = false;

    const finish = (result) => {
      if (settled) return;
      settled = true;
      socket.destroy();
      resolve(result);
    };

    socket.setTimeout(timeoutMs);
    socket.once('connect', () => {
      finish({ ok: true, remoteAddress: socket.remoteAddress, remotePort: socket.remotePort });
    });
    socket.once('timeout', () => finish({ ok: false, error: `TCP connect timeout after ${timeoutMs}ms` }));
    socket.once('error', (error) => finish({ ok: false, error: formatError(error) }));
  });
}

export async function testTlsHandshake(hostname, port, timeoutMs = 8_000) {
  return await new Promise((resolve) => {
    const socket = tls.connect({
      host: hostname,
      port,
      servername: hostname,
      rejectUnauthorized: true,
    });
    let settled = false;

    const finish = (result) => {
      if (settled) return;
      settled = true;
      socket.destroy();
      resolve(result);
    };

    socket.setTimeout(timeoutMs);
    socket.once('secureConnect', () => {
      finish({ ok: true, protocol: socket.getProtocol(), authorized: socket.authorized, authorizationError: socket.authorizationError ?? null });
    });
    socket.once('timeout', () => finish({ ok: false, error: `TLS handshake timeout after ${timeoutMs}ms` }));
    socket.once('error', (error) => finish({ ok: false, error: formatError(error) }));
  });
}
