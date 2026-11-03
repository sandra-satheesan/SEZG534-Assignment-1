import { createTaskService } from '../../src/services/tasks.service.js';

const tasks = [
  {
    id: '11111111-1111-4111-8111-111111111111',
    title: 'Lowercase',
    description: 'Details',
    priority: 'low',
    tags: ['work', 'api'],
    status: 'pending',
  },
  {
    id: '22222222-2222-4222-8222-222222222222',
    title: 'Uppercase',
    description: 'Details',
    priority: 'low',
    tags: ['Work', 'api'],
    status: 'pending',
  },
  {
    id: '33333333-3333-4333-8333-333333333333',
    title: 'One tag only',
    description: 'Details',
    priority: 'low',
    tags: ['work'],
    status: 'pending',
  },
];

describe('task tag filters (FR-009, TD-05)', () => {
  const service = createTaskService({
    repository: { readAll: async () => structuredClone(tasks) },
  });

  test('requires every requested tag', async () => {
    await expect(service.listTasks({ tags: ['work', 'api'] }))
      .resolves.toEqual([tasks[0]]);
  });

  test('matches tags case-sensitively and requires every requested value', async () => {
    await expect(service.listTasks({ tags: ['work', 'work'] }))
      .resolves.toEqual([tasks[0], tasks[2]]);
    await expect(service.listTasks({ tags: ['Work'] }))
      .resolves.toEqual([tasks[1]]);
  });
});
