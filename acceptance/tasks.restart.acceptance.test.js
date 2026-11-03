import { mkdtemp, rm } from 'node:fs/promises';
import { jest } from '@jest/globals';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { startAcceptanceServer } from './run-acceptance.js';

describe('100-cycle persistence restart acceptance (SC-004, FR-013, FR-016)', () => {
  jest.setTimeout(180_000);

  let directory;
  let tasksFile;
  let server;

  beforeAll(async () => {
    directory = await mkdtemp(path.join(tmpdir(), 'smart-todo-acceptance-restart-'));
    tasksFile = path.join(directory, 'tasks.json');
    server = await startAcceptanceServer({ tasksFile });
  });

  afterAll(async () => {
    if (server) {
      await server.stop();
    }
    if (directory) {
      await rm(directory, { recursive: true, force: true });
    }
  });

  async function jsonRequest(serverInstance, route, options) {
    const response = await serverInstance.request(route, options);
    return { response, body: await response.json() };
  }

  test('each saved task remains unchanged after its own real server restart', async () => {
    for (let check = 1; check <= 100; check += 1) {
      const create = await jsonRequest(server, '/api/tasks', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          title: `Restart check ${check}`,
          description: `Persisted details for restart check ${check}`,
          priority: ['low', 'medium', 'high'][check % 3],
          tags: [`check-${check}`, 'restart'],
        }),
      });

      expect(create.response.status).toBe(201);
      const savedTask = create.body.data;

      await server.stop();
      server = await startAcceptanceServer({ tasksFile });

      const retrieved = await jsonRequest(server, `/api/tasks/${savedTask.id}`);
      expect(retrieved.response.status).toBe(200);
      expect(retrieved.body).toEqual({ data: savedTask });
    }
  });
});
