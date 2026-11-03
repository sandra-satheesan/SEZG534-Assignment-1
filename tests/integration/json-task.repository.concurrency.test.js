import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { createJsonTaskRepository } from '../../src/persistence/json-task.repository.js';

const tasksToSave = [
  {
    id: '11111111-1111-4111-8111-111111111111',
    title: 'Concurrent first',
    description: 'First concurrent task',
    priority: 'high',
    tags: [],
    status: 'pending',
  },
  {
    id: '22222222-2222-4222-8222-222222222222',
    title: 'Concurrent second',
    description: 'Second concurrent task',
    priority: 'low',
    tags: [],
    status: 'pending',
  },
];

describe('single-process repository mutation serialization (FR-013)', () => {
  let directory;

  beforeEach(async () => {
    directory = await mkdtemp(path.join(tmpdir(), 'smart-todo-concurrent-mutations-'));
  });

  afterEach(async () => {
    await rm(directory, { recursive: true, force: true });
  });

  test('persists both concurrent mutations without a lost update', async () => {
    const filePath = path.join(directory, 'tasks.json');
    const repository = createJsonTaskRepository(filePath);

    await Promise.all(tasksToSave.map((task) => repository.mutate((tasks) => ({
      tasks: [...tasks, task],
      result: task,
    }))));

    await expect(repository.readAll()).resolves.toEqual(tasksToSave);
    await expect(JSON.parse(await readFile(filePath, 'utf8'))).toEqual(tasksToSave);
  });
});
