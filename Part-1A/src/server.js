import { pathToFileURL } from 'node:url';
import { fileURLToPath } from 'node:url';
import { createApp } from './app.js';

const DEFAULT_TASKS_FILE = fileURLToPath(new URL('../data/tasks.json', import.meta.url));

function parsePort(value) {
  if (typeof value === 'string' && !/^\d+$/.test(value)) {
    throw new TypeError('PORT must be an integer between 0 and 65535');
  }
  const port = typeof value === 'number' ? value : Number(value);
  if (!Number.isInteger(port) || port < 0 || port > 65_535) {
    throw new TypeError('PORT must be an integer between 0 and 65535');
  }
  return port;
}

export async function startServer({
  host = process.env.HOST ?? '127.0.0.1',
  port = process.env.PORT ?? 3000,
  tasksFile = process.env.TASKS_FILE ?? DEFAULT_TASKS_FILE,
  logger = console,
} = {}) {
  const parsedPort = parsePort(port);
  const server = createApp({ tasksFile, logger }).listen(parsedPort, host);
  await new Promise((resolve, reject) => {
    server.once('listening', resolve);
    server.once('error', reject);
  });

  const address = server.address();
  const actualHost = address.address.includes(':') ? `[${address.address}]` : address.address;
  logger.info(`READY http://${actualHost}:${address.port}`);
  return server;
}

export function stopServer(server) {
  if (!server?.listening) {
    return Promise.resolve();
  }

  return new Promise((resolve, reject) => {
    server.close((error) => {
      if (error) {
        reject(error);
        return;
      }
      resolve();
    });
  });
}

async function run() {
  const server = await startServer();
  let shuttingDown = false;

  const shutdown = async (signal) => {
    if (shuttingDown) {
      return;
    }
    shuttingDown = true;
    try {
      await stopServer(server);
      console.info(`STOPPED ${signal}`);
    } catch (error) {
      console.error('Server shutdown failed', error);
      process.exitCode = 1;
    }
  };

  process.once('SIGINT', () => void shutdown('SIGINT'));
  process.once('SIGTERM', () => void shutdown('SIGTERM'));
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  run().catch((error) => {
    console.error('Server failed to start', error);
    process.exitCode = 1;
  });
}
