import { createTaskService } from '../../src/services/tasks.service.js';

const existingTask = {
  id: '11111111-1111-4111-8111-111111111111',
  title: 'Original title',
  description: 'Original description',
  priority: 'low',
  tags: ['old'],
  status: 'pending',
};

function createRepository(initialTasks = [existingTask]) {
  let tasks = initialTasks;
  return {
    readAll: async () => structuredClone(tasks),
    mutate: async (mutator) => {
      const mutation = await mutator(structuredClone(tasks));
      tasks = mutation.tasks;
      return structuredClone(mutation.result);
    },
  };
}

describe('partial task updates (FR-004)', () => {
  test('changes supplied fields and preserves fields omitted from the update', async () => {
    const service = createTaskService({ repository: createRepository() });

    await expect(service.updateTask(existingTask.id, { title: 'Updated title' }))
      .resolves.toEqual({
        ...existingTask,
        title: 'Updated title',
      });
  });

  test('allows completed-task detail edits while retaining completed status', async () => {
    const completedTask = { ...existingTask, status: 'completed' };
    const service = createTaskService({
      repository: createRepository([completedTask]),
    });

    await expect(service.updateTask(existingTask.id, {
      title: 'Completed title',
      description: 'Completed details',
      priority: 'high',
      tags: ['new'],
    })).resolves.toEqual({
      ...completedTask,
      title: 'Completed title',
      description: 'Completed details',
      priority: 'high',
      tags: ['new'],
    });
  });

  test('returns not found without mutating for an unknown ID', async () => {
    const repository = createRepository();
    const service = createTaskService({ repository });

    await expect(service.updateTask(
      '22222222-2222-4222-8222-222222222222',
      { title: 'Changed' },
    )).rejects.toMatchObject({ status: 404, code: 'NOT_FOUND' });
    await expect(repository.readAll()).resolves.toEqual([existingTask]);
  });
});
