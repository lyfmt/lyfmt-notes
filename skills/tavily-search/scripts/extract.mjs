#!/usr/bin/env node

import { getApiKey, tavilyPost } from './_client.mjs';

function usage() {
  console.error(`Usage: extract.mjs "url1" ["url2" ...]`);
  process.exit(2);
}

const args = process.argv.slice(2);
if (args.length === 0 || args[0] === '-h' || args[0] === '--help') usage();

const urls = args.filter((a) => !a.startsWith('-'));

if (urls.length === 0) {
  console.error('No URLs provided');
  usage();
}

const apiKey = getApiKey();
if (!apiKey) {
  console.error('Missing TAVILY_API_KEY');
  process.exit(1);
}

let data;
try {
  data = await tavilyPost('extract', {
    api_key: apiKey,
    urls,
  }, 'extract');
} catch (error) {
  console.error(String(error?.message ?? error));
  process.exit(1);
}

const results = data.results ?? [];
const failed = data.failed_results ?? [];

for (const r of results) {
  const url = String(r?.url ?? '').trim();
  const content = String(r?.raw_content ?? '').trim();

  console.log(`# ${url}\n`);
  console.log(content || '(no content extracted)');
  console.log('\n---\n');
}

if (failed.length > 0) {
  console.log('## Failed URLs\n');
  for (const f of failed) {
    console.log(`- ${f.url}: ${f.error}`);
  }
}
