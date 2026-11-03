import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { startAcceptanceServer } from './run-acceptance.js';

describe('task filters and sorting acceptance (FR-006, FR-007, FR-009, FR-010, FR-012, FR-015, FR-016)', () => {
  let directory;
  let server;
  let tasks;

  beforeEach(async () => {
    directory = await mkdtemp(path.join(tmpdir(), 'smart-todo-acceptance-filters-'));
    server = await startAcceptanceServer({
      tasksFile: path.join(directory, 'tasks.json'),
    });
    tasks = [];
    for (const [title, priority, tags] of [
      ['First medium', 'medium', ['work', 'api']],
      ['Low uppercase', 'low', ['Work', 'api']],
      ['High', 'high', ['api']],
      ['Second medium', 'medium', ['work']],
    ]) {
      const created = await jsonRequest(server, '/api/tasks', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          title,
          description: `${title} details`,
          priority,
          tags,
        }),
      });
      expect(created.response.status).toBe(201);
      tasks.push(created.body.data);
    }

    await jsonRequest(server, `/api/tasks/${tasks[1].id}`, {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ status: 'in-progress' }),
    });
    await jsonRequest(server, `/api/tasks/${tasks[2].id}`, {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ status: 'in-progress' }),
    });
    await jsonRequest(server, `/api/tasks/${tasks[2].id}`, {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ status: 'completed' }),
    });
    tasks[1].status = 'in-progress';
    tasks[2].status = 'completed';
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

  function queryRoute(parameters) {
    const query = new URLSearchParams(parameters);
    return `/api/tasks?${query}`;
  }

  test('filters independently and combines dimensions with AND semantics', async () => {
    const status = await jsonRequest(server, queryRoute([['status', 'pending']]));
    const priority = await jsonRequest(server, queryRoute([['priority', 'high']]));
    const combined = await jsonRequest(server, queryRoute([
      ['status', 'pending'],
      ['priority', 'medium'],
      ['tag', ' work '],
      ['tag', 'api'],
    ]));
    const empty = await jsonRequest(server, queryRoute([
      ['status', 'pending'],
      ['priority', 'low'],
    ]));

    expect(status.response.status).toBe(200);
    expect(status.body).toEqual({ data: [tasks[0], tasks[3]] });
    expect(priority.body).toEqual({ data: [tasks[2]] });
    expect(combined.body).toEqual({ data: [tasks[0]] });
    expect(empty.response.status).toBe(200);
    expect(empty.body).toEqual({ data: [] });
  });

  test('requires every requested tag and matches trimmed tags case-sensitively', async () => {
    const repeated = await jsonRequest(server, queryRoute([
      ['tag', ' work '],
      ['tag', 'api'],
    ]));
    const duplicate = await jsonRequest(server, queryRoute([
      ['tag', 'work'],
      ['tag', ' work '],
    ]));
    const caseSensitive = await jsonRequest(server, queryRoute([['tag', 'Work']]));

    expect(repeated.body).toEqual({ data: [tasks[0]] });
    expect(duplicate.body).toEqual({ data: [tasks[0], tasks[3]] });
    expect(caseSensitive.body).toEqual({ data: [tasks[1]] });
  });

  test('sorts priority descending with stable ties without changing collection order', async () => {
    const sorted = await jsonRequest(server, '/api/tasks?sort=priority');
    const collection = await jsonRequest(server, '/api/tasks');

    expect(sorted.response.status).toBe(200);
    expect(sorted.body.data.map((task) => task.id)).toEqual([
      tasks[2].id,
      tasks[0].id,
      tasks[3].id,
      tasks[1].id,
    ]);
    expect(collection.body.data).toEqual(tasks);
  });

  test.each([
    '/api/tasks?status=unknown',
    '/api/tasks?priority=urgent',
    '/api/tasks?sort=created',
    '/api/tasks?tag=%20%20',
    '/api/tasks?status=pending&status=completed',
  ])('rejects invalid query %s with the documented error envelope', async (route) => {
    const result = await jsonRequest(server, route);

    expect(result.response.status).toBe(400);
    expect(result.body.error).toMatchObject({
      code: 'VALIDATION_ERROR',
      message: expect.any(String),
    });
  });
});
