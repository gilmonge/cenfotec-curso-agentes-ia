// Local consistency checks for the Spec Kit feature documents. No network/I/O
// beyond reading the workspace and no secret or user-content output.
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const feature = path.join(root, 'specs/002-chat-agente-analista');
const required = [
  'spec.md', 'plan.md', 'tasks.md', 'research.md', 'data-model.md', 'quickstart.md',
  'contracts/rest-api.yaml', 'contracts/mcp-tools.yaml', 'contracts/opencode-v2.md',
  'evidence/preflight-results.md', 'evidence/implementation-progress.md',
];
const failures = [];
for (const relative of required) {
  try { await fs.access(path.join(feature, relative)); }
  catch { failures.push(`missing:${relative}`); }
}

const docs = ['plan.md', 'tasks.md', 'quickstart.md', 'data-model.md', 'contracts/rest-api.yaml'];
const contents = new Map();
for (const relative of docs) contents.set(relative, await fs.readFile(path.join(feature, relative), 'utf8'));
const tasks = contents.get('tasks.md');
if (!/^- \[ \] T001\b/m.test(tasks)) failures.push('T001-generation-not-left-pending');
if ((tasks.match(/^- \[[ xX]\] T001\b/gm) || []).length !== 1) failures.push('T001-check-count');
if (!tasks.includes('contracts/opencode-v2.md') || tasks.includes('opencode-v1.md')) failures.push('tasks-contract-reference');
if (!/OpenCode `?2\.0\.27`?\s*(?:\([^)]*API v2\)|\/ API v2|API v2)/.test(contents.get('plan.md'))) failures.push('plan-version-contract');
if (!contents.get('quickstart.md').includes('GET /api/info')) failures.push('quickstart-api-info');
if (contents.get('quickstart.md').includes('Confirma `0.2.27`')) failures.push('quickstart-stale-v1-instruction');
if (!contents.get('quickstart.md').includes('OPENCODE_MODEL_ID')) failures.push('quickstart-model-selection');
if (!contents.get('contracts/rest-api.yaml').includes('OPENCODE_RATE_LIMITED')) failures.push('rest-contract-rate-limit-code');
if (!contents.get('contracts/rest-api.yaml').includes('MODEL_UNAVAILABLE')) failures.push('rest-contract-model-code');

const agentConfig = JSON.parse(await fs.readFile(path.join(root, 'opencode.jsonc'), 'utf8'));
if (agentConfig.agents?.analista?.model) failures.push('project-agent-fixes-model');
if (agentConfig.agents?.analista?.permissions?.[0]?.effect !== 'deny') failures.push('project-agent-not-deny-all');
const clientSource = await fs.readFile(path.join(root, 'agentes/analista/core/opencode_client.py'), 'utf8');
if (!clientSource.includes('"providerID": "opencode"')) failures.push('client-does-not-select-opencode');
if (/ollama/i.test(clientSource)) failures.push('client-has-legacy-provider-reference');
if (!clientSource.includes('_has_zero_cost(match.get("cost"))')) failures.push('client-does-not-enforce-zero-cost-models');
const requirementText = await fs.readFile(path.join(root, 'agentes/analista/requirements.txt'), 'utf8');
if (/ollama/i.test(requirementText)) failures.push('backend-requires-legacy-provider');
const preflightSource = await fs.readFile(path.join(root, 'scripts/diagnostics/opencode-v2-t001.mjs'), 'utf8');
if (!preflightSource.includes('hasZeroCost(candidateModel)')) failures.push('preflight-does-not-enforce-zero-cost-models');

const markdownFiles = ['plan.md', 'tasks.md', 'research.md', 'data-model.md', 'quickstart.md', 'contracts/opencode-v2.md', 'evidence/preflight-results.md', 'evidence/implementation-progress.md'];
for (const relative of markdownFiles) {
  const source = await fs.readFile(path.join(feature, relative), 'utf8');
  for (const match of source.matchAll(/\[[^\]]*\]\(([^)]+)\)/g)) {
    const target = match[1].split('#')[0].trim();
    if (!target || /^[a-z][a-z\d+.-]*:/i.test(target) || target.startsWith('#')) continue;
    const resolved = path.resolve(path.dirname(path.join(feature, relative)), target);
    try { await fs.access(resolved); }
    catch { failures.push(`broken-link:${relative}:${target}`); }
  }
}

const implementationFiles = [
  'opencode.jsonc', 'agentes/analista/core/prompt_loader.py', 'agentes/analista/core/opencode_client.py',
  'agentes/analista/core/context_builder.py', 'agentes/analista/core/output_parser.py',
  'agentes/analista/core/orchestrator.py', 'agentes/analista/api/main.py',
  'agentes/analista/api/routes/health.py', 'agentes/analista/api/routes/conversations.py',
  'agentes/analista/api/errors.py', 'agentes/analista/core/observability.py',
];
for (const relative of implementationFiles) {
  try { await fs.access(path.join(root, relative)); }
  catch { failures.push(`missing-implementation:${relative}`); }
}

console.log(JSON.stringify({
  check: 'speckit-doc-consistency',
  checked_documents: required.length,
  checked_markdown_links: true,
  checked_implementation_paths: implementationFiles.length,
  t001_open_for_unverified_model_generation: !failures.includes('T001-generation-not-left-pending') && !failures.includes('T001-check-count'),
  passed: failures.length === 0,
  failures,
}));
process.exitCode = failures.length ? 1 : 0;
