// Isolated OpenCode v2 T001 preflight against the existing local server.
// Reads credentials only from the ignored workspace .env file and never prints
// credentials, prompts, assistant text, session IDs, or raw server errors.
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const BASE_URL = (process.env.OPENCODE_SERVER_URL || 'http://127.0.0.1:4096').replace(/\/$/, '');
const DENY_ALL = [{ action: '*', resource: '*', effect: 'deny' }];
const GENERATION_TOKEN = 'T001_GENERATION_OK';

function readEnv(raw) {
  const values = {};
  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#') || !trimmed.includes('=')) continue;
    const splitAt = trimmed.indexOf('=');
    const key = trimmed.slice(0, splitAt).trim();
    let value = trimmed.slice(splitAt + 1).trim();
    if (value.length > 1 && value[0] === value.at(-1) && ['"', "'"].includes(value[0])) {
      value = value.slice(1, -1);
    }
    values[key] = value;
  }
  return values;
}

const localEnv = readEnv(await fs.readFile(path.join(ROOT, '.env'), 'utf8'));
const username = localEnv.OPENCODE_SERVER_USERNAME || 'opencode';
const password = localEnv.OPENCODE_SERVER_PASSWORD;
if (!password || password === 'CAMBIAR_EN_ENTORNO_LOCAL') {
  throw new Error('OPENCODE_SERVER_PASSWORD no está configurada localmente');
}
const auth = `Basic ${Buffer.from(`${username}:${password}`, 'utf8').toString('base64')}`;

class ApiFailure extends Error {
  constructor(status, endpoint) {
    super(`OpenCode HTTP ${status} at ${endpoint}`);
    this.status = status;
    this.endpoint = endpoint;
  }
}

async function request(method, endpoint, body, timeoutMs = 30000) {
  let response;
  try {
    response = await fetch(`${BASE_URL}${endpoint}`, {
      method,
      headers: {
        Authorization: auth,
        Accept: 'application/json',
        ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch {
    throw new Error(`OpenCode no responde en ${BASE_URL}`);
  }
  const contentType = response.headers.get('content-type') || '';
  let data = null;
  if (response.ok && contentType.includes('json')) data = await response.json();
  if (!response.ok) throw new ApiFailure(response.status, endpoint);
  return { status: response.status, data, contentType };
}

const dataOf = (response) => response?.data?.data;
const encodedDirectory = (directory) => `?location[directory]=${encodeURIComponent(directory)}`;
const quoteId = (id) => encodeURIComponent(id);

function denyAllPresent(value) {
  if (Array.isArray(value)) return value.some(denyAllPresent);
  if (!value || typeof value !== 'object') return false;
  if (value.action === '*' && value.resource === '*' && value.effect === 'deny') return true;
  return Object.values(value).some(denyAllPresent);
}

function hasZeroCost(model) {
  const entries = model?.cost;
  if (!Array.isArray(entries) || entries.length === 0) return false;
  return entries.every((entry) => {
    if (!entry || typeof entry !== 'object') return false;
    if (Object.keys(entry).some((key) => !['input', 'output', 'cache', 'tier'].includes(key))) return false;
    if (entry.input !== 0 || entry.output !== 0) return false;
    const cache = entry.cache;
    if (!cache || typeof cache !== 'object' || cache.read !== 0 || cache.write !== 0) return false;
    if (entry.tier && (entry.tier.type !== 'context' || !Number.isInteger(entry.tier.size))) return false;
    return true;
  });
}

function assistantRecords(response) {
  const records = dataOf(response);
  if (!Array.isArray(records)) return [];
  return records.filter((record) => record?.type === 'assistant');
}

function assistantText(records) {
  for (const record of [...records].reverse()) {
    if (!record.time?.completed) continue;
    const text = (record.content || [])
      .filter((part) => part?.type === 'text')
      .map((part) => part.text || '')
      .join('');
    return { done: true, text, info: record };
  }
  return { done: false, text: '', info: {} };
}

async function waitForAssistant(session, timeoutMs) {
  const endpoint = `/api/session/${quoteId(session)}/message?limit=30&order=asc`;
  const deadline = Date.now() + timeoutMs;
  let records = [];
  while (Date.now() < deadline) {
    records = assistantRecords(await request('GET', endpoint, undefined, 12000));
    const complete = assistantText(records);
    if (complete.done) return { ...complete, records };
    await new Promise((resolve) => setTimeout(resolve, 400));
  }
  return { done: false, text: '', info: {}, records };
}

async function deleteAndVerify(session) {
  const endpoint = `/api/session/${quoteId(session)}`;
  const deleted = await request('DELETE', endpoint);
  if (deleted.status !== 204) return false;
  try {
    await request('GET', endpoint);
    return false;
  } catch (error) {
    return error instanceof ApiFailure && error.status === 404;
  }
}

async function createSession(tempRoot, model, title, agent = 'analista') {
  const created = await request('POST', '/api/session', {
    title,
    agent,
    ...(model ? { model: { providerID: model.providerID, id: model.modelID } } : {}),
    location: { directory: tempRoot },
    permissions: DENY_ALL,
  });
  const session = dataOf(created)?.id;
  if (!session) throw new Error('POST /api/session no devolvió Session.Info con id');
  return { session, info: dataOf(created) };
}

async function main() {
  const infoResponse = await request('GET', '/api/info');
  const info = infoResponse.data;
  if (!info || infoResponse.status !== 200) throw new Error('GET /api/info no devolvió ServerInfo');

  const tempRoot = ROOT;
  const temporaryAgentDirectory = path.join(ROOT, '.opencode', 'agents');
  const temporaryAgentPath = path.join(temporaryAgentDirectory, 't001-preflight.md');
  let createdAgentDirectory = false;
  const sessions = [];
  const result = {
    server_version: info.version,
    server_pid: info.pid,
    api_info_status: infoResponse.status,
    api_version: 'v2',
    authenticated: true,
  };
  try {
    if (await fs.access(temporaryAgentPath).then(() => true).catch(() => false)) {
      throw new Error('Ya existe .opencode/agents/t001-preflight.md; no se sobreescribirá');
    }
    await fs.mkdir(temporaryAgentDirectory, { recursive: true });
    createdAgentDirectory = true;
    await fs.writeFile(temporaryAgentPath, [
      '---',
      'description: Temporary isolated T001 agent',
      'mode: primary',
      'permissions:',
      '  - action: "*"',
      '    resource: "*"',
      '    effect: deny',
      '---',
      'For the first request, reply exactly T001_GENERATION_OK and do not use tools.',
      '',
    ].join('\n'), 'utf8');

    const query = encodedDirectory(tempRoot);
    // Give the running server's configuration watcher time to discover this agent.
    await new Promise((resolve) => setTimeout(resolve, 2000));
    const locationResponse = await request('GET', `/api/location${query}`);
    const locationInfo = locationResponse.data;
    const agentResponse = await request('GET', `/api/agent${query}`);
    const agents = dataOf(agentResponse) || [];
    const agent = agents.find((item) => item.id === 't001-preflight');
    const chosenAgent = agent?.id || '';
    if (!agent) throw new Error('El agente temporal v2 t001-preflight no se registró');
    result.temporary_agent_loaded = Boolean(agent);
    result.temporary_agent_agent_ids = agents.map((item) => item.id).sort();
    result.requested_location_matches = agentResponse.data?.location?.directory === tempRoot;
    result.project_location_available = Boolean(locationInfo?.project);
    result.agent_permission_deny_all = Boolean(agent && denyAllPresent(agent));
    result.temporary_agent_system_loaded = Boolean(agent?.system?.includes(GENERATION_TOKEN));

    const providers = dataOf(await request('GET', `/api/provider${query}`)) || [];
    const models = dataOf(await request('GET', `/api/model${query}`)) || [];
    const defaultModel = dataOf(await request('GET', `/api/model/default${query}`));
    const requestedModelId = process.env.T001_MODEL_ID || localEnv.OPENCODE_MODEL_ID || '';
    const candidateModel = requestedModelId
      ? models.find((item) => item.providerID === 'opencode' && item.modelID === requestedModelId && item.enabled)
      : (defaultModel?.providerID === 'opencode' ? defaultModel : null);
    const testModel = candidateModel && hasZeroCost(candidateModel) ? candidateModel : null;
    result.provider_ids = providers.map((item) => item.id).sort();
    result.available_model_count = models.length;
    result.default_provider = defaultModel?.providerID || null;
    result.default_model = defaultModel?.modelID || null;
    result.test_provider = testModel?.providerID || null;
    result.test_model = testModel?.modelID || null;
    result.model_listed_for_selection = Boolean(testModel);
    result.model_zero_cost_verified = Boolean(testModel);

    const allowGeneration = process.env.T001_ALLOW_MODEL_GENERATION === 'true'
      && Boolean(process.env.T001_MODEL_ID);
    {
      const generation = await createSession(tempRoot, testModel, 't001-v2-isolated-generation', chosenAgent);
      sessions.push(generation.session);
      result.session_created = true;
      result.session_permissions_echoed = denyAllPresent(generation.info);
      if (allowGeneration && testModel) {
        const promptEndpoint = `/api/session/${quoteId(generation.session)}/prompt`;
        const admission = await request('POST', promptEndpoint, {
          text: `Reply exactly with ${GENERATION_TOKEN}. Do not use tools.`,
        });
        result.message_admitted = Boolean(dataOf(admission) && typeof dataOf(admission) === 'object');
        const generated = await waitForAssistant(generation.session, 85000);
        result.real_generation_completed = generated.done;
        result.generation_token_present = generated.text.includes(GENERATION_TOKEN);
        result.response_model_provider = generated.info.model?.providerID || null;
        result.response_model_id = generated.info.model?.id || null;
        result.generation_finish = generated.info.finish || null;
        result.generation_error_type = generated.info.error?.type || null;
        result.generation_error_status = generated.info.error?.status || null;
        result.generation_error_body_present = Boolean(generated.info.error?.response?.body);

        await request('POST', promptEndpoint, {
          text: 'Use the shell tool to run exactly `echo T001_PERMISSION_SENTINEL`, then report the result.',
        });
        const permissionTurn = await waitForAssistant(generation.session, 45000);
        const shellParts = permissionTurn.records.flatMap((record) => record.content || [])
          .filter((part) => part?.type === 'tool' && part.name === 'shell');
        const shellErrors = shellParts.filter((part) => part.state?.status === 'error');
        const permissionDenied = shellErrors.some((part) => {
          try { return JSON.stringify(part.state?.error || {}).toLowerCase().includes('permission'); }
          catch { return false; }
        });
        result.permission_attempt_completed = permissionTurn.done;
        result.shell_tool_attempted = shellParts.length > 0;
        result.shell_tool_denied = shellErrors.length > 0 && permissionDenied;
        result.shell_tool_executed = shellParts.some((part) => part.executed === true);
        result.tool_restrictions_effective = result.agent_permission_deny_all
          && result.session_permissions_echoed && !result.shell_tool_executed;

        const cancellation = await createSession(tempRoot, testModel, 't001-v2-isolated-cancellation', chosenAgent);
        sessions.push(cancellation.session);
        const cancellationEndpoint = `/api/session/${quoteId(cancellation.session)}/prompt`;
        const cancelAdmission = await request('POST', cancellationEndpoint, {
          text: 'Generate a numbered list from 1 through 100000, one number per line. Continue without tools.',
        });
        result.cancel_message_admitted = Boolean(dataOf(cancelAdmission));
        await new Promise((resolve) => setTimeout(resolve, 200));
        const interrupted = await request('POST', `/api/session/${quoteId(cancellation.session)}/interrupt`);
        result.interrupt_reported_active = interrupted.data?.interrupted === true;
      } else {
        result.model_generation_skipped = true;
      }
    }

    const deletion = [];
    for (const session of [...sessions].reverse()) deletion.push(await deleteAndVerify(session));
    sessions.length = 0;
    result.sessions_deleted = deletion.length > 0 && deletion.every(Boolean);
    result.session_delete_count = deletion.length;
  } finally {
    for (const session of [...sessions].reverse()) {
      try { await deleteAndVerify(session); } catch { /* cleanup must not expose raw errors */ }
    }
    if (createdAgentDirectory) {
      await fs.rm(temporaryAgentPath, { force: true });
      const remaining = await fs.readdir(temporaryAgentDirectory).catch(() => ['keep']);
      if (remaining.length === 0) await fs.rmdir(temporaryAgentDirectory).catch(() => {});
    }
  }

  const required = [
    'temporary_agent_loaded', 'temporary_agent_system_loaded', 'agent_permission_deny_all',
    'session_created', 'session_permissions_echoed', 'sessions_deleted',
  ];
  result.structural_t001_checks_passed = required.every((key) => result[key] === true);
  result.all_t001_checks_passed = result.structural_t001_checks_passed
    && result.real_generation_completed === true
    && result.generation_token_present === true
    && result.tool_restrictions_effective === true
    && result.interrupt_reported_active === true;
  console.log(JSON.stringify(result));
  return result.all_t001_checks_passed ? 0 : 2;
}

try {
  process.exitCode = await main();
} catch (error) {
  const output = error instanceof ApiFailure
    ? { check_failed: 'http', status: error.status, path: error.endpoint }
    : { check_failed: 'preflight', reason: String(error.message || error).slice(0, 180) };
  console.log(JSON.stringify(output));
  process.exitCode = 2;
}
