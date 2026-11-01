import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { jest } from '@jest/globals';
import { tmpdir } from 'node:os';
import path from 'node:path';
import request from 'supertest';
import { createApp } from '../../src/app.js';

describe('task status transition API (FR-008)', () => {
  let directory;
  let filePath;
  let app;
  let task;

  beforeEach(async () => {
    directory = await mkdtemp(path.join(tmpdir(), 'smart-todo-transitions-'));
    filePath = path.join(directory, 'tasks.json');
    app = createApp({ tasksFile: filePath, logger: { error: jest.fn() } });
    const response = await request(app).post('/api/tasks').send({
      title: 'Lifecycle task',
      description: 'Lifecycle details',
      priority: 'medium',
      tags: [],
    });
    task = response.body.data;
  });

  afterEach(async () => {
    await rm(directory, { recursive: true, force: true });
  });

  test('accepts each forward transition exactly once', async () => {
    const inProgress = await request(app)
      .patch(`/api/tasks/${task.id}`)
      .send({ status: 'in-progress' });
    const completed = await request(app)
      .patch(`/api/tasks/${task.id}`)
      .send({ status: 'completed' });

    expect(inProgress.status).toBe(200);
    expect(inProgress.body.data.status).toBe('in-progress');
    expect(completed.status).toBe(200);
    expect(completed.body.data.status).toBe('completed');
  });

  test.each([
    { body: { status: 'completed' }, label: 'skips a state' },
    { body: { status: 'pending' }, label: 'repeats the current state' },
    {
      body: { title: 'Must remain original', status: 'completed' },
      label: 'combines a detail edit with a skipped state',
    },
  ])('rejects a request that $label without changing stored bytes', async ({ body }) => {
    const before = await readFile(filePath, 'utf8');
    const response = await request(app).patch(`/api/tasks/${task.id}`).send(body);

    expect(response.status).toBe(400);
    expect(response.body.error).toEqual({
      code: 'VALIDATION_ERROR',
      message: expect.any(String),
    });
    expect(await readFile(filePath, 'utf8')).toBe(before);
  });

  test('does not allow a completed task to move backward', async () => {
    await request(app).patch(`/api/tasks/${task.id}`).send({ status: 'in-progress' });
    await request(app).patch(`/api/tasks/${task.id}`).send({ status: 'completed' });
    const before = await readFile(filePath, 'utf8');

    const response = await request(app)
      .patch(`/api/tasks/${task.id}`)
      .send({ status: 'in-progress' });

    expect(response.status).toBe(400);
    expect(await readFile(filePath, 'utf8')).toBe(before);
  });
});
