import { readFile } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = fileURLToPath(new URL('../../', import.meta.url));

describe('supported runtime and dependency baseline', () => {
  test('uses Node.js 24, npm, ESM, and Express 5', async () => {
    const nodeMajor = Number(process.versions.node.split('.')[0]);
    expect(nodeMajor).toBe(24);

    const npm = spawnSync('npm', ['--version'], {
      cwd: projectRoot,
      encoding: 'utf8',
      shell: false,
    });
    expect(npm.error).toBeUndefined();
    expect(npm.status).toBe(0);
    expect(npm.stdout.trim()).toMatch(/^\d+\.\d+\.\d+/);

    const packageManifest = JSON.parse(
      await readFile(path.join(projectRoot, 'package.json'), 'utf8'),
    );
    expect(packageManifest.type).toBe('module');
    expect(packageManifest.engines.node).toBe('>=24 <25');

    const expressManifest = JSON.parse(
      await readFile(path.join(projectRoot, 'node_modules/express/package.json'), 'utf8'),
    );
    expect(expressManifest.version.split('.')[0]).toBe('5');
  });
});
