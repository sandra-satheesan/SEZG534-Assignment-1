import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import {
  startAcceptanceServer,
} from './run-acceptance.js';

describe('create and review tasks acceptance (FR-001, FR-002, FR-003, FR-010, FR-012, FR-013, FR-015, FR-016)', () => {
  let directory;
  let tasksFile;
  let server;

  beforeEach(async () => {
    directory = await mkdtemp(path.join(tmpdir(), 'smart-todo-acceptance-us1-'));
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

  test('creates unique tasks and retrieves collection and task through public HTTP', async () => {
    const first = await jsonRequest(server, '/api/tasks', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        title: 'First',
        description: 'First task',
        priority: 'high',
        tags: ['api'],
      }),
    });
    const second = await jsonRequest(server, '/api/tasks', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        title: 'Second',
        description: 'Second task',
        priority: 'low',
        tags: [],
      }),
    });

    expect(first.response.status).toBe(201);
    expect(first.response.headers.get('location')).toBe(`/api/tasks/${first.body.data.id}`);
    expect(first.body.data.status).toBe('pending');
    expect(second.response.status).toBe(201);
    expect(second.body.data.id).not.toBe(first.body.data.id);

    const collection = await jsonRequest(server, '/api/tasks');
    const individual = await jsonRequest(server, `/api/tasks/${first.body.data.id}`);

    expect(collection.response.status).toBe(200);
    expect(collection.body).toEqual({ data: [first.body.data, second.body.data] });
    expect(individual.response.status).toBe(200);
    expect(individual.body).toEqual({ data: first.body.data });
  });

  test('rejects invalid requests with no task creation and documented error envelopes', async () => {
    const invalidRequests = [
      { title: 'Missing tags', description: 'Details', priority: 'low' },
      {
        title: 'Bad priority',
        description: 'Details',
        priority: 'urgent',
        tags: [],
      },
      {
        title: 'Bad initial status',
        description: 'Details',
        priority: 'low',
        tags: [],
        status: 'completed',
      },
      {
        title: 'Unknown property',
        description: 'Details',
        priority: 'low',
        tags: [],
        extra: true,
      },
    ];

    for (const body of invalidRequests) {
      const { response, body: errorBody } = await jsonRequest(server, '/api/tasks', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(body),
      });

      expect(response.status).toBe(400);
      expect(errorBody.error.code).toBe('VALIDATION_ERROR');
      expect(errorBody.error.message).toEqual(expect.any(String));
    }

    await expect(jsonRequest(server, '/api/tasks')).resolves.toMatchObject({
      response: { status: 200 },
      body: { data: [] },
    });
  });

  test('retains task data after stopping and restarting the server process', async () => {
    const created = await jsonRequest(server, '/api/tasks', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        title: 'Survives restart',
        description: 'Restart verification',
        priority: 'medium',
        tags: ['persistent'],
      }),
    });
    expect(created.response.status).toBe(201);

    await server.stop();
    server = await startAcceptanceServer({ tasksFile });

    const afterRestart = await jsonRequest(
      server,
      `/api/tasks/${created.body.data.id}`,
    );
    expect(afterRestart.response.status).toBe(200);
    expect(afterRestart.body).toEqual(created.body);
  });
});
