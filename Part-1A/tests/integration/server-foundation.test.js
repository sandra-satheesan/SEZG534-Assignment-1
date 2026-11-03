import { mkdtemp, rm } from 'node:fs/promises';
import { jest } from '@jest/globals';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { startServer, stopServer } from '../../src/server.js';

describe('server lifecycle foundation (FR-013, FR-016)', () => {
  let directory;
  let server;

  beforeEach(async () => {
    directory = await mkdtemp(path.join(tmpdir(), 'smart-todo-server-'));
  });

  afterEach(async () => {
    if (server) {
      await stopServer(server);
      server = undefined;
    }
    await rm(directory, { recursive: true, force: true });
  });

  test('listens on an ephemeral loopback port and closes cleanly', async () => {
    server = await startServer({
      host: '127.0.0.1',
      port: 0,
      tasksFile: path.join(directory, 'tasks.json'),
      logger: { info: jest.fn(), error: jest.fn() },
    });
    const { port } = server.address();

    expect(port).toEqual(expect.any(Number));
    expect(port).toBeGreaterThan(0);

    const response = await fetch(`http://127.0.0.1:${port}/not-a-route`);

    expect(response.status).toBe(404);
    await expect(response.json()).resolves.toMatchObject({
      error: { code: 'NOT_FOUND' },
    });

    await stopServer(server);
    server = undefined;
    expect(server).toBeUndefined();
  });

  test.each(['-1', '65536', 'not-a-port'])('rejects invalid port configuration %s', async (port) => {
    await expect(startServer({
      host: '127.0.0.1',
      port,
      tasksFile: path.join(directory, 'tasks.json'),
    })).rejects.toThrow('PORT must be an integer between 0 and 65535');
  });
});
