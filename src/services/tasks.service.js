import { randomUUID } from 'node:crypto';
import { NotFoundError } from '../errors/app-error.js';
import { createTaskRecord } from '../models/task.js';

const ID_GENERATION_ATTEMPTS = 10;

function createUniqueId(tasks, idGenerator) {
  const existingIds = new Set(tasks.map((task) => task.id));

  for (let attempt = 0; attempt < ID_GENERATION_ATTEMPTS; attempt += 1) {
    const candidate = idGenerator();
    if (typeof candidate === 'string' && !existingIds.has(candidate)) {
      return candidate;
    }
  }

  throw new Error('Unable to generate a unique task ID');
}

export function createTaskService({
  repository,
  idGenerator = randomUUID,
} = {}) {
  if (!repository) {
    throw new TypeError('A task repository is required');
  }

  return Object.freeze({
    async createTask(input) {
      return repository.mutate((tasks) => {
        const id = createUniqueId(tasks, idGenerator);
        const task = createTaskRecord(input, id);
        return {
          tasks: [...tasks, task],
          result: task,
        };
      });
    },

    async listTasks() {
      return repository.readAll();
    },

    async getTask(id) {
      const tasks = await repository.readAll();
      const task = tasks.find((candidate) => candidate.id === id);
      if (!task) {
        throw new NotFoundError('Task not found');
      }
      return task;
    },
  });
}
