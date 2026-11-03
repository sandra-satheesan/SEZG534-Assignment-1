import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { jest } from '@jest/globals';
import { tmpdir } from 'node:os';
import path from 'node:path';
import request from 'supertest';
import { createApp } from '../../src/app.js';

describe('task creation API (FR-001, FR-010, FR-012, FR-013)', () => {
  let directory;
  let filePath;
  let app;

  beforeEach(async () => {
    directory = await mkdtemp(path.join(tmpdir(), 'smart-todo-create-'));
    filePath = path.join(directory, 'tasks.json');
    app = createApp({ tasksFile: filePath, logger: { error: jest.fn() } });
  });

  afterEach(async () => {
    await rm(directory, { recursive: true, force: true });
  });

  test('creates a valid task, defaults status, and persists the documented response', async () => {
    const response = await request(app)
      .post('/api/tasks')
      .send({
        title: '  Ship release  ',
        description: '  Publish the release  ',
        priority: 'high',
        tags: [' release ', 'release'],
      });

    expect(response.status).toBe(201);
    expect(response.headers.location).toBe(`/api/tasks/${response.body.data.id}`);
    expect(response.body).toEqual({
      data: {
        id: expect.stringMatching(
          /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
        ),
        title: 'Ship release',
        description: 'Publish the release',
        priority: 'high',
        tags: ['release'],
        status: 'pending',
      },
    });
    await expect(readFile(filePath, 'utf8')).resolves.toContain('"title": "Ship release"');
  });

  test('accepts explicit pending status and rejects other initial statuses', async () => {
    const valid = await request(app)
      .post('/api/tasks')
      .send({
        title: 'Task',
        description: 'Details',
        priority: 'low',
        tags: [],
        status: 'pending',
      });
    const invalid = await request(app)
      .post('/api/tasks')
      .send({
        title: 'Invalid task',
        description: 'Invalid details',
        priority: 'low',
        tags: [],
        status: 'completed',
      });

    expect(valid.status).toBe(201);
    expect(invalid.status).toBe(400);
    expect(invalid.body.error).toMatchObject({ code: 'VALIDATION_ERROR' });
    await expect(request(app).get('/api/tasks')).resolves.toMatchObject({
      status: 200,
      body: { data: [expect.objectContaining({ title: 'Task' })] },
    });
  });

  test.each([
    [{ description: 'Details', priority: 'low', tags: [] }, 'title'],
    [{ title: 'Task', priority: 'low', tags: [] }, 'description'],
    [{ title: 'Task', description: 'Details', tags: [] }, 'priority'],
    [{ title: 'Task', description: 'Details', priority: 'low' }, 'tags'],
    [{ title: '  ', description: 'Details', priority: 'low', tags: [] }, 'title'],
    [{ title: 'Task', description: '  ', priority: 'low', tags: [] }, 'description'],
  ])('rejects invalid create data %j without storing a task', async (partial, field) => {
    const response = await request(app).post('/api/tasks').send(partial);

    expect(response.status).toBe(400);
    expect(response.body.error).toMatchObject({ code: 'VALIDATION_ERROR' });
    expect(response.body.error.message).toContain(field);
    const collection = await request(app).get('/api/tasks');
    expect(collection.status).toBe(200);
    expect(collection.body).toEqual({ data: [] });
  });
});
