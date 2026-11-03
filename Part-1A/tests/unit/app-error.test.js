import {
  AppError,
  NotFoundError,
  PayloadTooLargeError,
  PersistenceError,
  ValidationError,
} from '../../src/errors/app-error.js';

describe('application errors (FR-010, FR-011, FR-014)', () => {
  test('exposes stable status, code, message, and a typed name', () => {
    const error = new ValidationError('Invalid request');

    expect(error).toBeInstanceOf(AppError);
    expect(error).toMatchObject({
      name: 'ValidationError',
      status: 400,
      code: 'VALIDATION_ERROR',
      message: 'Invalid request',
    });
  });

  test.each([
    [NotFoundError, 404, 'NOT_FOUND'],
    [PayloadTooLargeError, 413, 'PAYLOAD_TOO_LARGE'],
    [PersistenceError, 500, 'PERSISTENCE_ERROR'],
  ])('%s has its documented HTTP status and code', (ErrorType, status, code) => {
    expect(new ErrorType()).toMatchObject({ status, code });
  });
});
