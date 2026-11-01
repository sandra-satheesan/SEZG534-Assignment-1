import { randomUUID } from 'node:crypto';
import { NotFoundError, ValidationError } from '../errors/app-error.js';
import { createTaskRecord, isTaskRecord } from '../models/task.js';

const ID_GENERATION_ATTEMPTS = 10;
const NEXT_STATUS = new Map([
  ['pending', 'in-progress'],
  ['in-progress', 'completed'],
]);

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

    async updateTask(id, input) {
      return repository.mutate((tasks) => {
        const index = tasks.findIndex((candidate) => candidate.id === id);
        if (index === -1) {
          throw new NotFoundError('Task not found');
        }

        const currentTask = tasks[index];
        if (
          Object.hasOwn(input, 'status')
          && NEXT_STATUS.get(currentTask.status) !== input.status
        ) {
          throw new ValidationError('Requested status is not the next permitted transition');
        }

        const updatedTask = { ...currentTask, ...input };
        if (!isTaskRecord(updatedTask)) {
          throw new ValidationError('Updated task contains invalid fields');
        }

        const updatedTasks = [...tasks];
        updatedTasks[index] = updatedTask;
        return {
          tasks: updatedTasks,
          result: updatedTask,
        };
      });
    },

    async deleteTask(id) {
      return repository.mutate((tasks) => {
        const index = tasks.findIndex((candidate) => candidate.id === id);
        if (index === -1) {
          throw new NotFoundError('Task not found');
        }

        return {
          tasks: tasks.filter((task) => task.id !== id),
          result: { id, deleted: true },
        };
      });
    },
  });
}
