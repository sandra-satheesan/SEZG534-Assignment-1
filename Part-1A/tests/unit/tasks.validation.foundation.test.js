import {
  validateCreateTask,
  validateUpdateTask,
} from '../../src/validation/tasks.validation.js';

function runMiddleware(middleware, body) {
  const request = { body };
  let nextError;

  middleware(request, {}, (error) => {
    nextError = error;
  });

  return { request, error: nextError };
}

describe('task request validation (FR-001, FR-004, FR-010)', () => {
  test('accepts a valid create object and trims required text', () => {
    const { request, error } = runMiddleware(validateCreateTask, {
      title: '  Plan release  ',
      description: '  Prepare notes  ',
      priority: 'high',
      tags: [' release ', 'release', 'Release'],
    });

    expect(error).toBeUndefined();
    expect(request.body).toEqual({
      title: 'Plan release',
      description: 'Prepare notes',
      priority: 'high',
      tags: ['release', 'Release'],
    });
  });

  test.each([
    [null, 'must be a JSON object'],
    [[], 'must be a JSON object'],
    [{ title: 'Task', description: 'Details', priority: 'low' }, 'tags'],
    [{
      title: 'Task',
      description: 'Details',
      priority: 'urgent',
      tags: [],
    }, 'priority'],
    [{
      title: 'Task',
      description: 'Details',
      priority: 'low',
      tags: ['   '],
    }, 'tags'],
    [{
      title: 'Task',
      description: 'Details',
      priority: 'low',
      tags: [],
      extra: true,
    }, 'extra'],
    [{
      title: 'Task',
      description: 'Details',
      priority: 'low',
      tags: [],
      status: 'completed',
    }, 'status'],
  ])('rejects invalid create body %j', (body, expectedMessage) => {
    const { error } = runMiddleware(validateCreateTask, body);

    expect(error).toMatchObject({
      code: 'VALIDATION_ERROR',
      status: 400,
    });
    expect(error.message).toContain(expectedMessage);
  });

  test('accepts valid partial updates without requiring omitted fields', () => {
    const { request, error } = runMiddleware(validateUpdateTask, {
      description: ' Revised details ',
    });

    expect(error).toBeUndefined();
    expect(request.body).toEqual({ description: 'Revised details' });
  });

  test.each([
    [{}, 'at least one field'],
    [{ id: 'caller-controlled' }, 'id'],
    [{ title: '   ' }, 'title'],
    [{ priority: 'urgent' }, 'priority'],
    [{ tags: [], status: 'done' }, 'status'],
  ])('rejects invalid update body %j', (body, expectedMessage) => {
    const { error } = runMiddleware(validateUpdateTask, body);

    expect(error).toMatchObject({
      code: 'VALIDATION_ERROR',
      status: 400,
    });
    expect(error.message).toContain(expectedMessage);
  });
});
