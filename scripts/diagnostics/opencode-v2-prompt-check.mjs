// Narrow T007 recheck for the new strict local/server prompt comparison.
// Reads Basic Auth only from the ignored root .env and prints booleans only.
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const env = await fs.readFile(path.join(root, '.env'), 'utf8');
const values = Object.fromEntries(env.split(/\r?\n/).flatMap((line) => {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith('#')) return [];
  const split = trimmed.indexOf('=');
  if (split < 0) return [];
  const key = trimmed.slice(0, split).trim();
  let value = trimmed.slice(split + 1).trim();
  if (value.length > 1 && value[0] === value.at(-1) && ['"', "'"].includes(value[0])) value = value.slice(1, -1);
  return [[key, value]];
}));
const username = values.OPENCODE_SERVER_USERNAME || 'opencode';
const password = values.OPENCODE_SERVER_PASSWORD;
if (!password || password === 'CAMBIAR_EN_ENTORNO_LOCAL') throw new Error('Falta la credencial local requerida');
const base = (values.OPENCODE_SERVER_URL || 'http://127.0.0.1:4096').replace(/\/$/, '');
const authorization = `Basic ${Buffer.from(`${username}:${password}`, 'utf8').toString('base64')}`;
const directory = encodeURIComponent(root);
const response = await fetch(`${base}/api/agent?location[directory]=${directory}`, {
  headers: { Authorization: authorization, Accept: 'application/json' },
  signal: AbortSignal.timeout(10000),
});
const result = { http_status: response.status, agent_found: false, system_loaded: false, exact_prompt_match: false, deny_all: false };
if (response.ok && (response.headers.get('content-type') || '').includes('json')) {
  const body = await response.json();
  const agents = body?.data;
  const agent = Array.isArray(agents) ? agents.find((item) => item?.id === 'analista') : null;
  result.agent_found = Boolean(agent);
  const localPrompt = (await fs.readFile(path.join(root, 'agentes/analista/prompts/sistema.md'), 'utf8')).trim();
  const serverPrompt = typeof agent?.system === 'string' ? agent.system.trim() : '';
  result.system_loaded = Boolean(serverPrompt);
  result.exact_prompt_match = Boolean(serverPrompt && serverPrompt === localPrompt);
  const permissions = agent?.permissions ?? agent?.permission;
  result.deny_all = Array.isArray(permissions) && permissions.some((item) => item?.action === '*' && item?.resource === '*' && item?.effect === 'deny');
}
console.log(JSON.stringify(result));
