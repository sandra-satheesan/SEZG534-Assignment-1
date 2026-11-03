import { mkdtemp, rm } from 'node:fs/promises';
import { jest } from '@jest/globals';
import { tmpdir } from 'node:os';
import path from 'node:path';
import request from 'supertest';
import { createApp } from '../../src/app.js';

describe('create request size limit (TD-03)', () => {
  let directory;
  let app;

  beforeEach(async () => {
    directory = await mkdtemp(path.join(tmpdir(), 'smart-todo-size-'));
    app = createApp({
      tasksFile: path.join(directory, 'tasks.json'),
      logger: { error: jest.fn() },
    });
  });

  afterEach(async () => {
    await rm(directory, { recursive: true, force: true });
  });

  test('accepts a valid JSON create request exactly 10 KiB long', async () => {
    const task = {
      title: 'Task',
      description: '',
      priority: 'low',
      tags: [],
    };
    const emptyDescriptionSize = Buffer.byteLength(JSON.stringify(task));
    task.description = 'x'.repeat(10_240 - emptyDescriptionSize);
    const body = JSON.stringify(task);
    expect(Buffer.byteLength(body)).toBe(10_240);

    const response = await request(app)
      .post('/api/tasks')
      .set('Content-Type', 'application/json')
      .send(body);

    expect(response.status).toBe(201);
  });

  test('rejects oversized JSON with 413 and makes no task mutation', async () => {
    const body = JSON.stringify({
      title: 'Task',
      description: 'x'.repeat(10_240),
      priority: 'low',
      tags: [],
    });
    expect(Buffer.byteLength(body)).toBeGreaterThan(10_240);

    const response = await request(app)
      .post('/api/tasks')
      .set('Content-Type', 'application/json')
      .send(body);

    expect(response.status).toBe(413);
    expect(response.body.error).toEqual({
      code: 'PAYLOAD_TOO_LARGE',
      message: 'JSON request body exceeds 10 KiB',
    });
    await expect(request(app).get('/api/tasks')).resolves.toMatchObject({
      status: 200,
      body: { data: [] },
    });
  });
});
