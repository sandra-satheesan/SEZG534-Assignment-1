import { createTaskService } from '../../src/services/tasks.service.js';

const task = {
  id: '11111111-1111-4111-8111-111111111111',
  title: 'Read task',
  description: 'Read task details',
  priority: 'high',
  tags: ['api'],
  status: 'pending',
};

describe('task identity and retrieval service (FR-002, FR-003, FR-011)', () => {
  const service = createTaskService({
    repository: { readAll: async () => [task] },
  });

  test('returns the collection and a task selected by ID', async () => {
    await expect(service.listTasks()).resolves.toEqual([task]);
    await expect(service.getTask(task.id)).resolves.toEqual(task);
  });

  test('returns a typed 404 for an unknown task ID', async () => {
    await expect(service.getTask('22222222-2222-4222-8222-222222222222'))
      .rejects.toMatchObject({ status: 404, code: 'NOT_FOUND' });
  });
});
