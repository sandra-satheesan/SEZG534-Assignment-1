import { mkdtemp, rm } from 'node:fs/promises';
import { jest } from '@jest/globals';
import { tmpdir } from 'node:os';
import path from 'node:path';
import request from 'supertest';
import { createApp } from '../../src/app.js';

describe('create request validation (TD-04)', () => {
  let directory;
  let app;

  beforeEach(async () => {
    directory = await mkdtemp(path.join(tmpdir(), 'smart-todo-validation-'));
    app = createApp({
      tasksFile: path.join(directory, 'tasks.json'),
      logger: { error: jest.fn() },
    });
  });

  afterEach(async () => {
    await rm(directory, { recursive: true, force: true });
  });

  test('rejects unknown create properties with a 400 JSON error and no task created', async () => {
    const response = await request(app)
      .post('/api/tasks')
      .send({
        title: 'Task',
        description: 'Details',
        priority: 'low',
        tags: [],
        id: 'caller-controlled',
      });

    expect(response.status).toBe(400);
    expect(response.body).toEqual({
      error: {
        code: 'VALIDATION_ERROR',
        message: 'Unknown request property: id',
      },
    });
    await expect(request(app).get('/api/tasks')).resolves.toMatchObject({
      status: 200,
      body: { data: [] },
    });
  });
});
