import { createTaskService } from '../../src/services/tasks.service.js';

const tasks = [
  {
    id: '11111111-1111-4111-8111-111111111111',
    title: 'First medium',
    description: 'Details',
    priority: 'medium',
    tags: [],
    status: 'pending',
  },
  {
    id: '22222222-2222-4222-8222-222222222222',
    title: 'Low',
    description: 'Details',
    priority: 'low',
    tags: [],
    status: 'pending',
  },
  {
    id: '33333333-3333-4333-8333-333333333333',
    title: 'High',
    description: 'Details',
    priority: 'high',
    tags: [],
    status: 'pending',
  },
  {
    id: '44444444-4444-4444-8444-444444444444',
    title: 'Second medium',
    description: 'Details',
    priority: 'medium',
    tags: [],
    status: 'pending',
  },
];

describe('priority sorting (FR-007)', () => {
  test('sorts high-to-low, keeps collection order for ties, and does not mutate repository order', async () => {
    const repository = { readAll: async () => structuredClone(tasks) };
    const service = createTaskService({ repository });

    await expect(service.listTasks({ sort: 'priority' })).resolves.toEqual([
      tasks[2],
      tasks[0],
      tasks[3],
      tasks[1],
    ]);
    await expect(service.listTasks()).resolves.toEqual(tasks);
  });
});
