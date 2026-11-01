import {
  AppError,
  PayloadTooLargeError,
  PersistenceError,
  ValidationError,
} from '../errors/app-error.js';

function normalizeError(error) {
  if (error instanceof AppError) {
    if (error.code === 'PERSISTENCE_ERROR') {
      return new PersistenceError();
    }
    return error;
  }

  if (error?.type === 'entity.too.large') {
    return new PayloadTooLargeError();
  }

  if (error?.type === 'entity.parse.failed') {
    return new ValidationError('Malformed JSON request body', { cause: error });
  }

  if (error?.type === 'charset.unsupported' || error?.type === 'encoding.unsupported') {
    return new ValidationError('Unsupported request encoding', { cause: error });
  }

  return new AppError('An unexpected error occurred', {
    status: 500,
    code: 'INTERNAL_ERROR',
    cause: error,
  });
}

export function errorHandler({ logger = console } = {}) {
  return (error, request, response, next) => {
    if (response.headersSent) {
      next(error);
      return;
    }

    const applicationError = normalizeError(error);
    if (applicationError.status >= 500) {
      logger.error({
        event: 'request.error',
        method: request.method,
        path: request.path,
        error: error.message,
        stack: error.stack,
      });
    }

    response.status(applicationError.status).json({
      error: {
        code: applicationError.code,
        message: applicationError.message,
      },
    });
  };
}
