import { mkdtemp, rm } from 'node:fs/promises';
import { jest } from '@jest/globals';
import { tmpdir } from 'node:os';
import path from 'node:path';
import request from 'supertest';
import { createApp } from '../../src/app.js';

describe('task filtering API (FR-006, FR-010, FR-012)', () => {
  let directory;
  let app;
  let tasks;

  beforeEach(async () => {
    directory = await mkdtemp(path.join(tmpdir(), 'smart-todo-filters-'));
    app = createApp({
      tasksFile: path.join(directory, 'tasks.json'),
      logger: { error: jest.fn() },
    });
    tasks = [];
    for (const task of [
      { title: 'Pending API', priority: 'high', tags: ['api', 'work'] },
      { title: 'Active work', priority: 'medium', tags: ['work'] },
      { title: 'Completed API', priority: 'low', tags: ['api'] },
    ]) {
      const response = await request(app).post('/api/tasks').send({
        ...task,
        description: `${task.title} details`,
      });
      expect(response.status).toBe(201);
      tasks.push(response.body.data);
    }

    await request(app).patch(`/api/tasks/${tasks[1].id}`).send({ status: 'in-progress' });
    await request(app).patch(`/api/tasks/${tasks[2].id}`).send({ status: 'in-progress' });
    await request(app).patch(`/api/tasks/${tasks[2].id}`).send({ status: 'completed' });
    tasks[1].status = 'in-progress';
    tasks[2].status = 'completed';
  });

  afterEach(async () => {
    await rm(directory, { recursive: true, force: true });
  });

  test('applies individual and combined filters with AND semantics', async () => {
    const status = await request(app).get('/api/tasks').query({ status: 'pending' });
    const priority = await request(app).get('/api/tasks').query({ priority: 'medium' });
    const combined = await request(app)
      .get('/api/tasks')
      .query({ status: 'pending', priority: 'high', tag: 'api' });
    const empty = await request(app)
      .get('/api/tasks')
      .query({ status: 'pending', priority: 'low' });

    expect(status.status).toBe(200);
    expect(status.body).toEqual({ data: [tasks[0]] });
    expect(priority.status).toBe(200);
    expect(priority.body).toEqual({ data: [tasks[1]] });
    expect(combined.status).toBe(200);
    expect(combined.body).toEqual({ data: [tasks[0]] });
    expect(empty.status).toBe(200);
    expect(empty.body).toEqual({ data: [] });
  });
});
