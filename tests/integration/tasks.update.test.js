import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { jest } from '@jest/globals';
import { tmpdir } from 'node:os';
import path from 'node:path';
import request from 'supertest';
import { createApp } from '../../src/app.js';

describe('task update API (FR-004, FR-010, FR-011, FR-012)', () => {
  let directory;
  let filePath;
  let app;
  let task;

  beforeEach(async () => {
    directory = await mkdtemp(path.join(tmpdir(), 'smart-todo-update-'));
    filePath = path.join(directory, 'tasks.json');
    app = createApp({ tasksFile: filePath, logger: { error: jest.fn() } });
    const created = await request(app).post('/api/tasks').send({
      title: 'Original title',
      description: 'Original details',
      priority: 'low',
      tags: ['old'],
    });
    task = created.body.data;
  });

  afterEach(async () => {
    await rm(directory, { recursive: true, force: true });
  });

  test('updates supplied details, preserves omitted fields, and returns the standard envelope', async () => {
    const response = await request(app)
      .patch(`/api/tasks/${task.id}`)
      .send({ title: '  Updated title  ', tags: [' new ', 'new'] });

    expect(response.status).toBe(200);
    expect(response.body).toEqual({
      data: {
        ...task,
        title: 'Updated title',
        tags: ['new'],
      },
    });
    await expect(request(app).get(`/api/tasks/${task.id}`)).resolves.toMatchObject({
      body: response.body,
    });
  });

  test('allows detail edits after completion without changing completed status', async () => {
    await request(app).patch(`/api/tasks/${task.id}`).send({ status: 'in-progress' });
    await request(app).patch(`/api/tasks/${task.id}`).send({ status: 'completed' });

    const response = await request(app)
      .patch(`/api/tasks/${task.id}`)
      .send({
        title: 'Finished title',
        description: 'Finished details',
        priority: 'high',
        tags: [' finished '],
      });

    expect(response.status).toBe(200);
    expect(response.body.data).toMatchObject({
      title: 'Finished title',
      description: 'Finished details',
      priority: 'high',
      tags: ['finished'],
      status: 'completed',
    });
  });

  test.each([
    { body: {}, label: 'empty update' },
    { body: { title: '   ' }, label: 'blank title' },
    { body: { description: 12 }, label: 'non-string description' },
    { body: { priority: 'urgent' }, label: 'invalid priority' },
    { body: { tags: ['  '] }, label: 'blank tag' },
    { body: { unexpected: true }, label: 'unknown property' },
  ])('rejects $label and leaves the task unchanged', async ({ body }) => {
    const before = await readFile(filePath, 'utf8');
    const response = await request(app).patch(`/api/tasks/${task.id}`).send(body);

    expect(response.status).toBe(400);
    expect(response.body.error.code).toBe('VALIDATION_ERROR');
    expect(await readFile(filePath, 'utf8')).toBe(before);
  });

  test('returns 404 and preserves data when updating an unknown task', async () => {
    const before = await readFile(filePath, 'utf8');
    const response = await request(app)
      .patch('/api/tasks/22222222-2222-4222-8222-222222222222')
      .send({ title: 'Missing task' });

    expect(response.status).toBe(404);
    expect(response.body.error.code).toBe('NOT_FOUND');
    expect(await readFile(filePath, 'utf8')).toBe(before);
  });
});
