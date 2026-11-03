import { createTaskService } from '../../src/services/tasks.service.js';

const tasks = [
  {
    id: '11111111-1111-4111-8111-111111111111',
    title: 'Pending API',
    description: 'Pending task',
    priority: 'high',
    tags: ['api', 'work'],
    status: 'pending',
  },
  {
    id: '22222222-2222-4222-8222-222222222222',
    title: 'Active work',
    description: 'Active task',
    priority: 'medium',
    tags: ['work'],
    status: 'in-progress',
  },
  {
    id: '33333333-3333-4333-8333-333333333333',
    title: 'Completed API',
    description: 'Completed task',
    priority: 'low',
    tags: ['api'],
    status: 'completed',
  },
];

describe('task collection filters (FR-006)', () => {
  const service = createTaskService({
    repository: { readAll: async () => structuredClone(tasks) },
  });

  test('filters by status and priority independently', async () => {
    await expect(service.listTasks({ status: 'pending' }))
      .resolves.toEqual([tasks[0]]);
    await expect(service.listTasks({ priority: 'medium' }))
      .resolves.toEqual([tasks[1]]);
  });

  test('combines status, priority, and tags with AND semantics', async () => {
    await expect(service.listTasks({
      status: 'pending',
      priority: 'high',
      tags: ['api', 'work'],
    })).resolves.toEqual([tasks[0]]);
    await expect(service.listTasks({
      status: 'pending',
      priority: 'low',
    })).resolves.toEqual([]);
  });

  test('returns an empty collection when filters match no tasks', async () => {
    await expect(service.listTasks({ status: 'completed', priority: 'high' }))
      .resolves.toEqual([]);
  });
});
