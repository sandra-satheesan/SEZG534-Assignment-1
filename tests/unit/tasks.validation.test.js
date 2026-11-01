import {
  validateCreateTask,
} from '../../src/validation/tasks.validation.js';

function validate(body) {
  let error;
  const request = { body };
  validateCreateTask(request, {}, (nextError) => {
    error = nextError;
  });
  return { request, error };
}

describe('create task tag normalization (FR-001, TD-05)', () => {
  test('trims tags and removes exact duplicates while preserving first occurrence', () => {
    const { request, error } = validate({
      title: 'Task',
      description: 'Details',
      priority: 'low',
      tags: [' work ', 'Work', 'work', ' work '],
    });

    expect(error).toBeUndefined();
    expect(request.body.tags).toEqual(['work', 'Work']);
  });

  test.each([
    ['   '],
    [1],
    [null],
  ])('rejects invalid tag %j', (tag) => {
    const { error } = validate({
      title: 'Task',
      description: 'Details',
      priority: 'low',
      tags: [tag],
    });

    expect(error).toMatchObject({ status: 400, code: 'VALIDATION_ERROR' });
  });

  test('allows an empty tags list', () => {
    const { request, error } = validate({
      title: 'Task',
      description: 'Details',
      priority: 'low',
      tags: [],
    });

    expect(error).toBeUndefined();
    expect(request.body.tags).toEqual([]);
  });
});
