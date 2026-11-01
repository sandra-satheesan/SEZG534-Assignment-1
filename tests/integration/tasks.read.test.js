import { mkdtemp, rm } from 'node:fs/promises';
import { jest } from '@jest/globals';
import { tmpdir } from 'node:os';
import path from 'node:path';
import request from 'supertest';
import { createApp } from '../../src/app.js';

describe('task retrieval API (FR-002, FR-003, FR-011, FR-012)', () => {
  let directory;
  let app;

  beforeEach(async () => {
    directory = await mkdtemp(path.join(tmpdir(), 'smart-todo-read-'));
    app = createApp({
      tasksFile: path.join(directory, 'tasks.json'),
      logger: { error: jest.fn() },
    });
  });

  afterEach(async () => {
    await rm(directory, { recursive: true, force: true });
  });

  async function createTask(title) {
    const response = await request(app)
      .post('/api/tasks')
      .send({
        title,
        description: `${title} details`,
        priority: 'medium',
        tags: [],
      });
    expect(response.status).toBe(201);
    return response.body.data;
  }

  test('lists all tasks and retrieves one by ID with stable response envelopes', async () => {
    const first = await createTask('First');
    const second = await createTask('Second');
    const list = await request(app).get('/api/tasks');
    const individual = await request(app).get(`/api/tasks/${first.id}`);

    expect(first.id).not.toBe(second.id);
    expect(list.status).toBe(200);
    expect(list.body).toEqual({ data: [first, second] });
    expect(individual.status).toBe(200);
    expect(individual.body).toEqual({ data: first });
  });

  test('returns 404 for an unknown but well-formed task ID', async () => {
    const response = await request(app)
      .get('/api/tasks/22222222-2222-4222-8222-222222222222');

    expect(response.status).toBe(404);
    expect(response.body).toEqual({
      error: { code: 'NOT_FOUND', message: 'Task not found' },
    });
  });
});
