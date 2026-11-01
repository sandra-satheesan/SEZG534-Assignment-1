import express from 'express';
import { jest } from '@jest/globals';
import request from 'supertest';
import { createApp } from '../../src/app.js';
import {
  NotFoundError,
  PersistenceError,
  ValidationError,
} from '../../src/errors/app-error.js';

describe('Express application foundation (FR-010, FR-012, FR-014, FR-015)', () => {
  const repository = { readAll: jest.fn() };
  const logger = { error: jest.fn() };
  const app = createApp({ repository, logger });

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('injects application dependencies without opening a listening socket', () => {
    expect(app.locals.repository).toBe(repository);
    expect(app.locals.logger).toBe(logger);
    expect(app.listening).toBeUndefined();
    expect(app.listen).toBeInstanceOf(Function);
  });

  test('returns a consistent JSON 404 response for an unknown route', async () => {
    const response = await request(app).get('/not-a-route');

    expect(response.status).toBe(404);
    expect(response.body).toEqual({
      error: {
        code: 'NOT_FOUND',
        message: 'Route not found',
      },
    });
  });

  test('maps typed errors to the documented JSON envelope', async () => {
    const testApp = express();
    testApp.get('/invalid', (req, res, next) => {
      next(new ValidationError('Invalid value'));
    });
    testApp.get('/missing', (req, res, next) => {
      next(new NotFoundError('Task not found'));
    });
    testApp.get('/storage-failure', (req, res, next) => {
      next(new PersistenceError('/private/path/secret.json'));
    });
    const { errorHandler } = await import('../../src/middleware/error-handler.js');
    testApp.use(errorHandler({ logger }));

    await expect(request(testApp).get('/invalid')).resolves.toMatchObject({
      status: 400,
      body: { error: { code: 'VALIDATION_ERROR', message: 'Invalid value' } },
    });
    await expect(request(testApp).get('/missing')).resolves.toMatchObject({
      status: 404,
      body: { error: { code: 'NOT_FOUND', message: 'Task not found' } },
    });
    const storageFailure = await request(testApp).get('/storage-failure');
    expect(storageFailure.status).toBe(500);
    expect(storageFailure.body).toEqual({
      error: {
        code: 'PERSISTENCE_ERROR',
        message: 'Task storage operation failed',
      },
    });
    expect(JSON.stringify(storageFailure.body)).not.toContain('secret.json');
  });

  test('rejects malformed JSON and JSON bodies larger than 10 KiB consistently', async () => {
    const malformed = await request(app)
      .post('/not-a-route')
      .set('Content-Type', 'application/json')
      .send('{"broken":');

    expect(malformed.status).toBe(400);
    expect(malformed.body.error).toMatchObject({ code: 'VALIDATION_ERROR' });

    const boundaryBody = `{"value":"${'x'.repeat(10_228)}"}`;
    expect(Buffer.byteLength(boundaryBody)).toBe(10_240);
    const boundary = await request(app)
      .post('/not-a-route')
      .set('Content-Type', 'application/json')
      .send(boundaryBody);

    expect(boundary.status).toBe(404);
    expect(boundary.body.error).toMatchObject({ code: 'NOT_FOUND' });

    const oversized = await request(app)
      .post('/not-a-route')
      .set('Content-Type', 'application/json')
      .send(JSON.stringify({ value: 'x'.repeat(10_240) }));

    expect(oversized.status).toBe(413);
    expect(oversized.body.error).toMatchObject({ code: 'PAYLOAD_TOO_LARGE' });
  });

  test('does not expose unexpected error details in responses', async () => {
    const testApp = express();
    testApp.get('/failure', () => {
      throw new Error('/private/path/secret.json');
    });
    const { errorHandler } = await import('../../src/middleware/error-handler.js');
    testApp.use(errorHandler({ logger }));

    const response = await request(testApp).get('/failure');

    expect(response.status).toBe(500);
    expect(response.body).toEqual({
      error: {
        code: 'INTERNAL_ERROR',
        message: 'An unexpected error occurred',
      },
    });
    expect(JSON.stringify(response.body)).not.toContain('secret.json');
    expect(logger.error).toHaveBeenCalledTimes(1);
  });
});
