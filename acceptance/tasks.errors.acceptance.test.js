import { chmod, mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { startAcceptanceServer } from './run-acceptance.js';

describe('request and persistence error acceptance (FR-010, FR-012, FR-014, FR-015, FR-016)', () => {
  let directory;
  let tasksFile;
  let server;
  let writeFailureFixtureActive = false;

  beforeEach(async () => {
    directory = await mkdtemp(path.join(tmpdir(), 'smart-todo-acceptance-errors-'));
    tasksFile = path.join(directory, 'tasks.json');
    server = await startAcceptanceServer({ tasksFile });
  });

  afterEach(async () => {
    try {
      if (server) {
        await server.stop();
      }
    } finally {
      server = undefined;
      if (directory) {
        try {
          if (writeFailureFixtureActive) {
            if (process.platform === 'win32') {
              await chmod(tasksFile, 0o600);
            } else {
              await chmod(directory, 0o700);
            }
          }
        } finally {
          await rm(directory, { recursive: true, force: true });
          directory = undefined;
          tasksFile = undefined;
          writeFailureFixtureActive = false;
        }
      }
    }
  });

  async function jsonRequest(serverInstance, route, options) {
    const response = await serverInstance.request(route, options);
    return { response, body: await response.json() };
  }

  test('returns consistent JSON errors for malformed, invalid, unknown, and oversized requests without mutation', async () => {
    const malformed = await server.request('/api/tasks', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: '{',
    });
    const malformedBody = await malformed.json();
    expect(malformed.status).toBe(400);
    expect(malformedBody.error).toMatchObject({
      code: 'VALIDATION_ERROR',
      message: expect.any(String),
    });

    const invalid = await jsonRequest(server, '/api/tasks', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        title: 'Invalid task',
        description: 'Invalid details',
        priority: 'urgent',
        tags: [],
      }),
    });
    const unknown = await jsonRequest(server, '/api/tasks', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        title: 'Unknown field',
        description: 'Invalid details',
        priority: 'low',
        tags: [],
        extra: true,
      }),
    });
    const oversizedBody = JSON.stringify({
      title: 'x'.repeat(10_300),
      description: 'Oversized body',
      priority: 'low',
      tags: [],
    });
    const oversized = await server.request('/api/tasks', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: oversizedBody,
    });
    const oversizedError = await oversized.json();

    for (const result of [invalid, unknown]) {
      expect(result.response.status).toBe(400);
      expect(result.body.error).toMatchObject({
        code: 'VALIDATION_ERROR',
        message: expect.any(String),
      });
    }
    expect(oversizedBody.length).toBeGreaterThan(10_240);
    expect(oversized.status).toBe(413);
    expect(oversizedError.error).toMatchObject({
      code: 'PAYLOAD_TOO_LARGE',
      message: expect.any(String),
    });

    const collection = await jsonRequest(server, '/api/tasks');
    expect(collection.response.status).toBe(200);
    expect(collection.body).toEqual({ data: [] });
  });

  test('reports malformed stored JSON as a safe persistence error', async () => {
    await server.stop();
    await writeFile(tasksFile, '{');
    server = await startAcceptanceServer({ tasksFile });

    const result = await jsonRequest(server, '/api/tasks');

    expect(result.response.status).toBe(500);
    expect(result.body).toEqual({
      error: {
        code: 'PERSISTENCE_ERROR',
        message: 'Task storage operation failed',
      },
    });
    expect(JSON.stringify(result.body)).not.toContain(directory);
  });

  test('reports unreadable storage through the public HTTP error contract', async () => {
    await server.stop();
    await rm(tasksFile, { force: true });
    await mkdir(tasksFile);
    server = await startAcceptanceServer({ tasksFile });

    const result = await jsonRequest(server, '/api/tasks');

    expect(result.response.status).toBe(500);
    expect(result.body.error).toEqual({
      code: 'PERSISTENCE_ERROR',
      message: 'Task storage operation failed',
    });
    expect(JSON.stringify(result.body)).not.toContain(directory);
  });

  test('does not claim success when storage cannot be written', async () => {
    const initialized = await jsonRequest(server, '/api/tasks');
    expect(initialized.response.status).toBe(200);
    expect(initialized.body).toEqual({ data: [] });

    if (process.platform === 'win32') {
      await chmod(tasksFile, 0o444);
    } else {
      await chmod(directory, 0o555);
    }
    writeFailureFixtureActive = true;

    const readable = await jsonRequest(server, '/api/tasks');
    expect(readable.response.status).toBe(200);
    expect(readable.body).toEqual({ data: [] });

    const result = await jsonRequest(server, '/api/tasks', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        title: 'Cannot persist',
        description: 'This mutation must fail',
        priority: 'high',
        tags: [],
      }),
    });

    expect(result.response.status).toBe(500);
    expect(result.body.error).toEqual({
      code: 'PERSISTENCE_ERROR',
      message: 'Task storage operation failed',
    });
    expect(JSON.stringify(result.body)).not.toContain(directory);

    const unchanged = await jsonRequest(server, '/api/tasks');
    expect(unchanged.response.status).toBe(200);
    expect(unchanged.body).toEqual({ data: [] });
  });
});
