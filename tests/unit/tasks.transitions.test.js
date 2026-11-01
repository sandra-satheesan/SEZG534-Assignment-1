import { createTaskService } from '../../src/services/tasks.service.js';

const initialTask = {
  id: '11111111-1111-4111-8111-111111111111',
  title: 'Lifecycle task',
  description: 'Lifecycle details',
  priority: 'medium',
  tags: [],
  status: 'pending',
};

function createRepository() {
  let tasks = [structuredClone(initialTask)];
  return {
    readAll: async () => structuredClone(tasks),
    mutate: async (mutator) => {
      const mutation = await mutator(structuredClone(tasks));
      tasks = mutation.tasks;
      return structuredClone(mutation.result);
    },
  };
}

describe('task status transitions (FR-008)', () => {
  test('accepts pending to in-progress to completed', async () => {
    const service = createTaskService({ repository: createRepository() });

    await expect(service.updateTask(initialTask.id, { status: 'in-progress' }))
      .resolves.toMatchObject({ status: 'in-progress' });
    await expect(service.updateTask(initialTask.id, { status: 'completed' }))
      .resolves.toMatchObject({ status: 'completed' });
  });

  test.each([
    ['pending', 'completed'],
    ['pending', 'pending'],
    ['in-progress', 'pending'],
    ['completed', 'in-progress'],
    ['completed', 'pending'],
    ['in-progress', 'in-progress'],
  ])('rejects transition from %s to %s without applying any fields', async (from, to) => {
    const task = { ...initialTask, status: from };
    const repository = createRepository();
    if (from !== 'pending') {
      await repository.mutate(() => ({
        tasks: [task],
        result: task,
      }));
    }
    const service = createTaskService({ repository });

    await expect(service.updateTask(initialTask.id, {
      title: 'Must not be applied',
      status: to,
    })).rejects.toMatchObject({ status: 400, code: 'VALIDATION_ERROR' });
    await expect(repository.readAll()).resolves.toEqual([task]);
  });
});
