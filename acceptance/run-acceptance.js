import { mkdtemp, rm } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const projectRoot = fileURLToPath(new URL('../', import.meta.url));
const serverEntry = fileURLToPath(new URL('../src/server.js', import.meta.url));
const jestEntry = fileURLToPath(new URL('../node_modules/jest/bin/jest.js', import.meta.url));

function waitForReadiness(child, timeoutMs) {
  return new Promise((resolve, reject) => {
    let output = '';
    const timeout = setTimeout(() => {
      reject(new Error(`Server readiness was not received within ${timeoutMs} ms`));
    }, timeoutMs);

    const cleanup = () => {
      clearTimeout(timeout);
      child.stdout.off('data', onStdout);
      child.stderr.off('data', onStderr);
      child.off('error', onError);
      child.off('exit', onExit);
    };

    const onOutput = (chunk) => {
      output += chunk.toString();
      const readiness = output.match(/^READY (http:\/\/\S+)$/m);
      if (readiness) {
        cleanup();
        resolve(readiness[1]);
      }
    };
    const onStdout = (chunk) => onOutput(chunk);
    const onStderr = (chunk) => onOutput(chunk);
    const onError = (error) => {
      cleanup();
      reject(error);
    };
    const onExit = (code, signal) => {
      cleanup();
      reject(new Error(
        `Server exited before readiness (code ${code}, signal ${signal}): ${output}`,
      ));
    };

    child.stdout.on('data', onStdout);
    child.stderr.on('data', onStderr);
    child.once('error', onError);
    child.once('exit', onExit);
  });
}

export async function startAcceptanceServer({
  tasksFile,
  timeoutMs = 10_000,
} = {}) {
  let ownedDirectory;
  if (!tasksFile) {
    ownedDirectory = await mkdtemp(path.join(tmpdir(), 'smart-todo-acceptance-'));
    tasksFile = path.join(ownedDirectory, 'tasks.json');
  }

  const child = spawn(process.execPath, [serverEntry], {
    cwd: projectRoot,
    env: {
      ...process.env,
      HOST: '127.0.0.1',
      PORT: '0',
      TASKS_FILE: tasksFile,
    },
    stdio: ['ignore', 'pipe', 'pipe'],
    shell: false,
  });

  try {
    const baseUrl = await waitForReadiness(child, timeoutMs);
    return Object.freeze({
      baseUrl,
      process: child,
      request: (route, options) => fetch(new URL(route, `${baseUrl}/`), options),
      stop: async () => {
        try {
          await stopAcceptanceServer(child);
        } finally {
          if (ownedDirectory) {
            await rm(ownedDirectory, { recursive: true, force: true });
          }
        }
      },
    });
  } catch (error) {
    await stopAcceptanceServer(child);
    if (ownedDirectory) {
      await rm(ownedDirectory, { recursive: true, force: true });
    }
    throw error;
  }
}

export function stopAcceptanceServer(child) {
  if (
    child.pid === undefined
    || child.exitCode !== null
    || child.signalCode !== null
  ) {
    return Promise.resolve();
  }

  return new Promise((resolve, reject) => {
    const onError = (error) => {
      child.off('exit', onExit);
      reject(error);
    };
    const onExit = () => {
      child.off('error', onError);
      resolve();
    };
    child.once('error', onError);
    child.once('exit', onExit);
    child.kill('SIGTERM');
  });
}

export function runAcceptanceSuite() {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [
      '--experimental-vm-modules',
      jestEntry,
      '--runInBand',
      '--testMatch',
      '**/acceptance/**/*.acceptance.test.js',
    ], {
      cwd: projectRoot,
      stdio: 'inherit',
      shell: false,
    });

    child.once('error', reject);
    child.once('exit', (code, signal) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`Acceptance suite failed (code ${code}, signal ${signal})`));
      }
    });
  });
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  runAcceptanceSuite().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
