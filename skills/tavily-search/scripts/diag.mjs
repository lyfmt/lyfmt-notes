#!/usr/bin/env node

import {
  DEFAULT_API_BASE_URL,
  getApiBaseUrl,
  getApiKey,
  getTimeoutMs,
  resolveApiHost,
  testTcpConnect,
  testTlsHandshake,
} from './_client.mjs';

const apiKey = getApiKey();
const apiBaseUrl = getApiBaseUrl();
const timeoutMs = getTimeoutMs();

console.log('Tavily diag');
console.log('apiBaseUrl =', apiBaseUrl);
console.log('defaultApiBaseUrl =', DEFAULT_API_BASE_URL);
console.log('timeoutMs =', timeoutMs);
console.log('hasApiKey =', Boolean(apiKey), 'len =', apiKey.length, 'prefix =', apiKey ? apiKey.slice(0, 8) : '');
console.log('');

try {
  const { url, port, addresses } = await resolveApiHost();
  console.log('hostname =', url.hostname);
  console.log('port =', port);
  console.log('dns =', JSON.stringify(addresses));
  console.log('');

  const tcp = await testTcpConnect(url.hostname, port, Math.min(timeoutMs, 10_000));
  console.log('tcp =', JSON.stringify(tcp));

  const tls = await testTlsHandshake(url.hostname, port, Math.min(timeoutMs, 10_000));
  console.log('tls =', JSON.stringify(tls));
} catch (error) {
  console.error('diag failed:', String(error?.message ?? error));
  process.exit(1);
}
