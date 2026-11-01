import { mkdtemp, rm } from 'node:fs/promises';
import { jest } from '@jest/globals';
import { tmpdir } from 'node:os';
import path from 'node:path';
import request from 'supertest';
import { createApp } from '../../src/app.js';

describe('priority sorting API (FR-007, FR-010)', () => {
  let directory;
  let app;
  let created;

  beforeEach(async () => {
    directory = await mkdtemp(path.join(tmpdir(), 'smart-todo-sort-'));
    app = createApp({
      tasksFile: path.join(directory, 'tasks.json'),
      logger: { error: jest.fn() },
    });
    created = [];
    for (const [title, priority] of [
      ['First medium', 'medium'],
      ['Low', 'low'],
      ['High', 'high'],
      ['Second medium', 'medium'],
    ]) {
      const response = await request(app).post('/api/tasks').send({
        title,
        description: `${title} details`,
        priority,
        tags: [],
      });
      created.push(response.body.data);
    }
  });

  afterEach(async () => {
    await rm(directory, { recursive: true, force: true });
  });

  test('sorts high-to-low, retains tie order, and leaves persisted collection order intact', async () => {
    const sorted = await request(app).get('/api/tasks').query({ sort: 'priority' });
    const unsorted = await request(app).get('/api/tasks');

    expect(sorted.status).toBe(200);
    expect(sorted.body.data.map((task) => task.id)).toEqual([
      created[2].id,
      created[0].id,
      created[3].id,
      created[1].id,
    ]);
    expect(unsorted.body.data).toEqual(created);
  });

  test.each([
    { priority: 'urgent' },
    { sort: 'created' },
    { sort: ['priority', 'priority'] },
  ])('rejects invalid query parameters %j using the error envelope', async (query) => {
    const response = await request(app).get('/api/tasks').query(query);

    expect(response.status).toBe(400);
    expect(response.body.error).toMatchObject({
      code: 'VALIDATION_ERROR',
      message: expect.any(String),
    });
  });
});
