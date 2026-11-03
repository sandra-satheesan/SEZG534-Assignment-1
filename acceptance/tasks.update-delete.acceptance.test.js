import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { startAcceptanceServer } from './run-acceptance.js';

describe('update and delete acceptance (FR-004, FR-005, FR-008, FR-012, FR-013, FR-015, FR-016)', () => {
  let directory;
  let tasksFile;
  let server;

  beforeEach(async () => {
    directory = await mkdtemp(path.join(tmpdir(), 'smart-todo-acceptance-us2-'));
    tasksFile = path.join(directory, 'tasks.json');
    server = await startAcceptanceServer({ tasksFile });
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
    return jsonRequest(server, '/api/tasks', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        title: 'Original task',
        description: 'Original details',
        priority: 'low',
        tags: ['old'],
      }),
    });
  }

  test('updates fields, preserves omitted values and completed status, and persists across restart', async () => {
    const created = await createTask();
    expect(created.response.status).toBe(201);
    const taskId = created.body.data.id;

    const inProgress = await jsonRequest(server, `/api/tasks/${taskId}`, {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ status: 'in-progress' }),
    });
    expect(inProgress.response.status).toBe(200);

    const completed = await jsonRequest(server, `/api/tasks/${taskId}`, {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ status: 'completed' }),
    });
    expect(completed.response.status).toBe(200);

    const updated = await jsonRequest(server, `/api/tasks/${taskId}`, {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        title: '  Updated task  ',
        description: 'Updated description',
        priority: 'high',
        tags: [' new ', 'new'],
      }),
    });
    expect(updated.response.status).toBe(200);
    expect(updated.body).toEqual({
      data: {
        ...created.body.data,
        title: 'Updated task',
        description: 'Updated description',
        priority: 'high',
        tags: ['new'],
        status: 'completed',
      },
    });
    expect(updated.body.data.description).toBe('Updated description');
    expect(updated.body.data).toMatchObject({
      id: taskId,
      title: 'Updated task',
      description: 'Updated description',
      priority: 'high',
      tags: ['new'],
      status: 'completed',
    });

    await server.stop();
    server = await startAcceptanceServer({ tasksFile });
    const afterRestart = await jsonRequest(server, `/api/tasks/${taskId}`);
    expect(afterRestart.response.status).toBe(200);
    expect(afterRestart.body).toEqual(updated.body);

    const deleted = await jsonRequest(server, `/api/tasks/${taskId}`, {
      method: 'DELETE',
    });
    expect(deleted.response.status).toBe(200);
    expect(deleted.body).toEqual({ data: { id: taskId, deleted: true } });

    await server.stop();
    server = await startAcceptanceServer({ tasksFile });
    const missing = await jsonRequest(server, `/api/tasks/${taskId}`);
    expect(missing.response.status).toBe(404);
    expect(missing.body.error.code).toBe('NOT_FOUND');
  });
});
