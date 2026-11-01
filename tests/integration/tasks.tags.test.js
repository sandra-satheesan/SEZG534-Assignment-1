import { mkdtemp, rm } from 'node:fs/promises';
import { jest } from '@jest/globals';
import { tmpdir } from 'node:os';
import path from 'node:path';
import request from 'supertest';
import { createApp } from '../../src/app.js';

describe('task tag filtering API (FR-009, TD-05)', () => {
  let directory;
  let app;
  let created;

  beforeEach(async () => {
    directory = await mkdtemp(path.join(tmpdir(), 'smart-todo-tag-filter-'));
    app = createApp({
      tasksFile: path.join(directory, 'tasks.json'),
      logger: { error: jest.fn() },
    });
    created = [];
    for (const [title, tags] of [
      ['Lowercase', ['work', 'api']],
      ['Uppercase', ['Work', 'api']],
      ['One tag only', ['work']],
    ]) {
      const response = await request(app).post('/api/tasks').send({
        title,
        description: `${title} details`,
        priority: 'low',
        tags,
      });
      created.push(response.body.data);
    }
  });

  afterEach(async () => {
    await rm(directory, { recursive: true, force: true });
  });

  test('requires all repeated tag filters, trims and deduplicates values case-sensitively', async () => {
    const allTags = await request(app)
      .get('/api/tasks')
      .query({ tag: [' work ', 'api'] });
    const duplicateTags = await request(app)
      .get('/api/tasks')
      .query({ tag: [' work ', 'work'] });
    const caseSensitive = await request(app)
      .get('/api/tasks')
      .query({ tag: 'Work' });

    expect(allTags.status).toBe(200);
    expect(allTags.body.data).toEqual([created[0]]);
    expect(duplicateTags.status).toBe(200);
    expect(duplicateTags.body.data).toEqual([created[0], created[2]]);
    expect(caseSensitive.status).toBe(200);
    expect(caseSensitive.body.data).toEqual([created[1]]);
  });

  test('rejects an empty repeated tag filter instead of silently ignoring it', async () => {
    const response = await request(app).get('/api/tasks').query({ tag: ['api', '  '] });

    expect(response.status).toBe(400);
    expect(response.body.error.code).toBe('VALIDATION_ERROR');
  });
});
