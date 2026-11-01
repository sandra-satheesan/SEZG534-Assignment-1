import { jest } from '@jest/globals';
import { createTaskService } from '../../src/services/tasks.service.js';

describe('task creation service (FR-001, FR-002)', () => {
  test('creates a pending task with a unique ID', async () => {
    let tasks = [];
    const repository = {
      mutate: async (mutator) => {
        const mutation = await mutator(tasks);
        tasks = mutation.tasks;
        return mutation.result;
      },
    };
    const service = createTaskService({
      repository,
      idGenerator: () => '11111111-1111-4111-8111-111111111111',
    });

    await expect(service.createTask({
      title: 'Release notes',
      description: 'Prepare release notes',
      priority: 'medium',
      tags: [],
    })).resolves.toEqual({
      id: '11111111-1111-4111-8111-111111111111',
      title: 'Release notes',
      description: 'Prepare release notes',
      priority: 'medium',
      tags: [],
      status: 'pending',
    });
  });

  test('checks for ID collisions before inserting', async () => {
    const existing = {
      id: '11111111-1111-4111-8111-111111111111',
      title: 'Existing task',
      description: 'Existing details',
      priority: 'low',
      tags: [],
      status: 'pending',
    };
    let tasks = [existing];
    const repository = {
      mutate: async (mutator) => {
        const mutation = await mutator(tasks);
        tasks = mutation.tasks;
        return mutation.result;
      },
    };
    const candidates = [
      existing.id,
      '22222222-2222-4222-8222-222222222222',
    ];
    const idGenerator = jest.fn(() => candidates.shift());
    const service = createTaskService({ repository, idGenerator });

    const created = await service.createTask({
      title: 'New task',
      description: 'New details',
      priority: 'high',
      tags: [],
    });

    expect(created.id).toBe('22222222-2222-4222-8222-222222222222');
    expect(idGenerator).toHaveBeenCalledTimes(2);
    expect(tasks).toHaveLength(2);
    expect(new Set(tasks.map((task) => task.id)).size).toBe(2);
  });
});
