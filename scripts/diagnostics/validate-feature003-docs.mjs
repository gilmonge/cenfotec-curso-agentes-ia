// Consistency checks for the feature 003 specification and task state.
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const feature = path.join(root, 'specs/003-sistema-multiagente-rag');
const required = [
  'spec.md', 'plan.md', 'tasks.md', 'research.md', 'data-model.md', 'quickstart.md',
  'contracts/workflow-api.md', 'informe-pruebas.md',
];
const failures = [];
const contents = new Map();
for (const relative of required) {
  try { contents.set(relative, await fs.readFile(path.join(feature, relative), 'utf8')); }
  catch { failures.push(`missing:${relative}`); }
}

const tasks = contents.get('tasks.md') || '';
for (const task of ['T001', 'T002']) {
  if ((tasks.match(new RegExp(`^- \\[ \\] ${task}\\b`, 'gm')) || []).length !== 1) failures.push(`${task}-must-remain-pending`);
  if ((tasks.match(new RegExp(`^- \\[xX \\] ${task}\\b`, 'gm')) || []).length !== 0) failures.push(`${task}-must-not-be-completed`);
}
for (const task of ['T030', 'T031', 'T032', 'T053', 'T054']) {
  if ((tasks.match(new RegExp(`^- \\[x\\] ${task}\\b`, 'gmi')) || []).length > 1) failures.push(`${task}-duplicate-completion`);
}
if (!tasks.includes('ejemplos/polizas_demo/')) failures.push('tasks-missing-fixture-reference');
if (!tasks.includes('no se ejecutó la ingesta real')) failures.push('tasks-missing-remote-ingestion-boundary');

const [requirementsText, lockText] = await Promise.all([
  fs.readFile(path.join(root, 'agentes/analista/requirements.txt'), 'utf8'),
  fs.readFile(path.join(root, 'agentes/analista/requirements.lock'), 'utf8'),
]);
const normalizePackage = name => name.toLowerCase().replace(/[-_.]+/g, '-');
const lockedPins = new Map([...lockText.matchAll(/^([A-Za-z0-9_.-]+)==([^;\s]+)(?:\s*;[^\r\n]*)?/gm)]
  .map(([, name, version]) => [normalizePackage(name), version]));
for (const requirement of requirementsText.split(/\r?\n/)) {
  const line = requirement.trim();
  if (!line || line.startsWith('#')) continue;
  const match = line.match(/^([A-Za-z0-9_.-]+)==([^;\s]+)(?:\s*;.*)?$/);
  if (!match) {
    failures.push(`requirement-not-pinned:${line.split(/[\s;]/, 1)[0]}`);
    continue;
  }
  const [, name, version] = match;
  if (lockedPins.get(normalizePackage(name)) !== version) failures.push(`lock-mismatch:${name}`);
}

for (const relative of ['spec.md', 'plan.md', 'tasks.md', 'research.md', 'data-model.md', 'quickstart.md', 'contracts/workflow-api.md', 'informe-pruebas.md']) {
  const source = contents.get(relative);
  if (!source) continue;
  for (const match of source.matchAll(/\[[^\]]*\]\(([^)]+)\)/g)) {
    const target = match[1].split('#')[0].trim();
    if (!target || /^[a-z][a-z\d+.-]*:/i.test(target) || target.startsWith('#')) continue;
    const resolved = path.resolve(path.dirname(path.join(feature, relative)), target);
    try { await fs.access(resolved); }
    catch { failures.push(`broken-link:${relative}:${target}`); }
  }
}

console.log(JSON.stringify({
  check: 'feature003-doc-consistency',
  checked_documents: required.length,
  checked_markdown_links: true,
  checked_dependency_pins: true,
  t001_pending: /^- \[ \] T001\b/m.test(tasks),
  t002_pending: /^- \[ \] T002\b/m.test(tasks),
  passed: failures.length === 0,
  failures,
}));
process.exitCode = failures.length ? 1 : 0;
