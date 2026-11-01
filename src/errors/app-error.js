export class AppError extends Error {
  constructor(message, { status, code, cause } = {}) {
    super(message, cause === undefined ? undefined : { cause });
    this.name = new.target.name;
    this.status = status ?? 500;
    this.code = code ?? 'INTERNAL_ERROR';
  }
}

export class ValidationError extends AppError {
  constructor(message = 'Request validation failed', options = {}) {
    super(message, { status: 400, code: 'VALIDATION_ERROR', ...options });
  }
}

export class NotFoundError extends AppError {
  constructor(message = 'Resource not found', options = {}) {
    super(message, { status: 404, code: 'NOT_FOUND', ...options });
  }
}

export class PayloadTooLargeError extends AppError {
  constructor(message = 'JSON request body exceeds 10 KiB', options = {}) {
    super(message, { status: 413, code: 'PAYLOAD_TOO_LARGE', ...options });
  }
}

export class PersistenceError extends AppError {
  constructor(message = 'Task storage operation failed', options = {}) {
    super(message, { status: 500, code: 'PERSISTENCE_ERROR', ...options });
  }
}
