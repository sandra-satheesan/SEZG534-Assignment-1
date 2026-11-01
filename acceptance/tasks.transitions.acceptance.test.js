import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { startAcceptanceServer } from './run-acceptance.js';

describe('status transition acceptance (FR-008, FR-010, FR-011, FR-012, FR-015, FR-016)', () => {
  let directory;
  let server;

  beforeEach(async () => {
    directory = await mkdtemp(path.join(tmpdir(), 'smart-todo-acceptance-transitions-'));
    server = await startAcceptanceServer({
      tasksFile: path.join(directory, 'tasks.json'),
    });
  });

  afterEach(async () => {
    if (server) {
      await server.stop();
      server = undefined;
    }
    await rm(directory, { recursive: true, force: true });
  });

  async function jsonRequest(serverInstance, route, options) {
    const response = await serverInstance.request(route, options);
    return { response, body: await response.json() };
  }

  async function createTask() {
    const created = await jsonRequest(server, '/api/tasks', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        title: 'Transition task',
        description: 'Transition details',
        priority: 'medium',
        tags: [],
      }),
    });
    expect(created.response.status).toBe(201);
    return created.body.data;
  }

  test('allows each forward transition and rejects skipped, repeated, and backward transitions atomically', async () => {
    const task = await createTask();

    const skipped = await jsonRequest(server, `/api/tasks/${task.id}`, {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ title: 'Must not change', status: 'completed' }),
    });
    expect(skipped.response.status).toBe(400);
    expect(skipped.body.error.code).toBe('VALIDATION_ERROR');
    let current = await jsonRequest(server, `/api/tasks/${task.id}`);
    expect(current.body.data).toEqual(task);

    const advanced = await jsonRequest(server, `/api/tasks/${task.id}`, {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ status: 'in-progress' }),
    });
    expect(advanced.response.status).toBe(200);
    expect(advanced.body.data.status).toBe('in-progress');

    const repeated = await jsonRequest(server, `/api/tasks/${task.id}`, {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ status: 'in-progress' }),
    });
    expect(repeated.response.status).toBe(400);
    current = await jsonRequest(server, `/api/tasks/${task.id}`);
    expect(current.body.data.status).toBe('in-progress');

    const completed = await jsonRequest(server, `/api/tasks/${task.id}`, {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ status: 'completed' }),
    });
    expect(completed.response.status).toBe(200);

    const backward = await jsonRequest(server, `/api/tasks/${task.id}`, {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ status: 'pending' }),
    });
    expect(backward.response.status).toBe(400);
    current = await jsonRequest(server, `/api/tasks/${task.id}`);
    expect(current.body.data).toEqual(completed.body.data);
  });

  test('returns consistent 404 error envelopes for update and delete of unknown IDs', async () => {
    const unknownId = '22222222-2222-4222-8222-222222222222';
    const update = await jsonRequest(server, `/api/tasks/${unknownId}`, {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ title: 'Missing task' }),
    });
    const deletion = await jsonRequest(server, `/api/tasks/${unknownId}`, {
      method: 'DELETE',
    });

    for (const result of [update, deletion]) {
      expect(result.response.status).toBe(404);
      expect(result.body).toEqual({
        error: { code: 'NOT_FOUND', message: 'Task not found' },
      });
    }
  });
});
