import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const runId = new Date().toISOString().replaceAll(':', '-');
const directory = resolve('reports', runId);
mkdirSync(directory, { recursive: true });
const manifest = {
  runId,
  scope: 'MindVault frontend including Revision Journey; automated mock/DOM validation only',
  runtime: process.version,
  dependencyLockSha256: createHash('sha256').update(readFileSync('package-lock.json')).digest('hex'),
  costs: { externalServiceUsd: 0, agentCost: null, note: 'Agent billing is not exposed by this environment.' },
  callCounts: { backend: 0, ai: 0, database: 0 },
  cache: { npm: 'Project .npm-cache; warm after dependency installation', application: 'In-memory shared mock session; resets on full reload; no persistent cache' },
  liveValidation: { marker: '*.live.test.ts', status: 'NOT_RUN', reason: 'Frontend-only scope prohibits calling real services.' },
  checks: [],
};
const commands = [
  ['TypeScript', 'node_modules/typescript/bin/tsc', ['-b', '--pretty', 'false']],
  ['Production build', 'node_modules/vite/bin/vite.js', ['build']],
  ['Mock unit tests', 'node_modules/vitest/vitest.mjs', ['run']],
];
for (const [name, executable, args] of commands) {
  const start = Date.now();
  const result = spawnSync(process.execPath, [executable, ...args], { encoding: 'utf8', windowsHide: true });
  const output = `${result.stdout ?? ''}${result.stderr ?? ''}${result.error?.message ?? ''}`;
  process.stdout.write(`\n${name}\n${output}`);
  const log = `${name.toLowerCase().replaceAll(' ', '-')}.log`;
  writeFileSync(resolve(directory, log), output);
  manifest.checks.push({ name, command: [process.execPath, executable, ...args], exitCode: result.status, durationMs: Date.now() - start, status: result.status === 0 ? 'PASS' : 'FAIL', log });
  writeFileSync(resolve(directory, 'manifest.json'), JSON.stringify(manifest, null, 2));
}
console.log(`\nSaved run manifest: ${directory}`);
if (manifest.checks.some((check) => check.status !== 'PASS')) process.exitCode = 1;
