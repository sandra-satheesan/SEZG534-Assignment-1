import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { jest } from '@jest/globals';
import { tmpdir } from 'node:os';
import path from 'node:path';
import request from 'supertest';
import { createApp } from '../../src/app.js';
import { PersistenceError } from '../../src/errors/app-error.js';

describe('task deletion API (FR-005, FR-011, FR-014)', () => {
  let directory;
  let filePath;
  let app;
  let task;

  beforeEach(async () => {
    directory = await mkdtemp(path.join(tmpdir(), 'smart-todo-delete-'));
    filePath = path.join(directory, 'tasks.json');
    app = createApp({ tasksFile: filePath, logger: { error: jest.fn() } });
    const created = await request(app).post('/api/tasks').send({
      title: 'Delete task',
      description: 'Delete details',
      priority: 'low',
      tags: [],
    });
    task = created.body.data;
  });

  afterEach(async () => {
    await rm(directory, { recursive: true, force: true });
  });

  test('deletes a task and returns the documented result envelope', async () => {
    const response = await request(app).delete(`/api/tasks/${task.id}`);

    expect(response.status).toBe(200);
    expect(response.body).toEqual({ data: { id: task.id, deleted: true } });
    await expect(request(app).get(`/api/tasks/${task.id}`)).resolves.toMatchObject({
      status: 404,
      body: { error: { code: 'NOT_FOUND', message: 'Task not found' } },
    });
  });

  test('returns 404 without changing storage when deleting an unknown task', async () => {
    const before = await readFile(filePath, 'utf8');
    const response = await request(app)
      .delete('/api/tasks/22222222-2222-4222-8222-222222222222');

    expect(response.status).toBe(404);
    expect(response.body.error.code).toBe('NOT_FOUND');
    expect(await readFile(filePath, 'utf8')).toBe(before);
  });

  test('reports a persistence failure without claiming deletion succeeded', async () => {
    const repository = {
      readAll: async () => [task],
      mutate: async () => {
        throw new PersistenceError('internal persistence detail');
      },
    };
    const failingApp = createApp({
      repository,
      logger: { error: jest.fn() },
    });

    const response = await request(failingApp).delete(`/api/tasks/${task.id}`);

    expect(response.status).toBe(500);
    expect(response.body).toEqual({
      error: {
        code: 'PERSISTENCE_ERROR',
        message: 'Task storage operation failed',
      },
    });
  });
});
