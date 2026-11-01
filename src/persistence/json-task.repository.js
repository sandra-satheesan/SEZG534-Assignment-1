import { randomUUID } from 'node:crypto';
import * as defaultFileSystem from 'node:fs/promises';
import path from 'node:path';
import { PersistenceError } from '../errors/app-error.js';
import { isTaskCollection } from '../models/task.js';

function clone(value) {
  if (value === undefined) {
    return undefined;
  }
  return JSON.parse(JSON.stringify(value));
}

function validateCollection(value) {
  if (!isTaskCollection(value)) {
    throw new Error('Stored task collection contains invalid data');
  }
}

export function createJsonTaskRepository(
  filePath,
  { fileSystem = defaultFileSystem } = {},
) {
  if (typeof filePath !== 'string' || filePath.length === 0) {
    throw new TypeError('A task data file path is required');
  }

  const canonicalPath = path.resolve(filePath);
  let mutationQueue = Promise.resolve();

  function enqueue(operation) {
    const result = mutationQueue.then(operation);
    mutationQueue = result.then(() => undefined, () => undefined);
    return result;
  }

  async function loadTasks() {
    let contents;
    try {
      contents = await fileSystem.readFile(canonicalPath, 'utf8');
    } catch (error) {
      if (error.code !== 'ENOENT') {
        throw new PersistenceError('Unable to read task storage', { cause: error });
      }

      await replaceFile([]);
      return [];
    }

    let tasks;
    try {
      tasks = JSON.parse(contents);
      validateCollection(tasks);
    } catch (error) {
      throw new PersistenceError('Task storage contains invalid data', { cause: error });
    }

    return tasks;
  }

  async function replaceFile(tasks) {
    const directory = path.dirname(canonicalPath);
    const temporaryPath = path.join(
      directory,
      `.${path.basename(canonicalPath)}.${randomUUID()}.tmp`,
    );
    let fileHandle;
    let renamed = false;

    try {
      await fileSystem.mkdir(directory, { recursive: true });
      fileHandle = await fileSystem.open(temporaryPath, 'wx', 0o600);
      await fileHandle.writeFile(`${JSON.stringify(tasks, null, 2)}\n`, 'utf8');
      await fileHandle.sync();
      await fileHandle.close();
      fileHandle = undefined;
      await fileSystem.rename(temporaryPath, canonicalPath);
      renamed = true;
    } catch (error) {
      if (fileHandle) {
        await fileHandle.close().catch((cleanupError) => {
          error.cleanupError = cleanupError;
        });
      }
      if (!renamed) {
        await fileSystem.unlink(temporaryPath).catch((cleanupError) => {
          if (cleanupError.code !== 'ENOENT') {
            error.cleanupError = cleanupError;
          }
        });
      }
      throw new PersistenceError('Unable to persist task storage', { cause: error });
    }
  }

  return Object.freeze({
    async readAll() {
      return enqueue(async () => clone(await loadTasks()));
    },

    async mutate(mutator) {
      if (typeof mutator !== 'function') {
        throw new TypeError('A mutation callback is required');
      }

      return enqueue(async () => {
        const currentTasks = await loadTasks();
        const mutation = await mutator(clone(currentTasks));
        if (
          mutation === null
          || typeof mutation !== 'object'
          || !Object.hasOwn(mutation, 'tasks')
        ) {
          throw new TypeError('A mutation must return a tasks array');
        }

        try {
          validateCollection(mutation.tasks);
        } catch (error) {
          throw new PersistenceError('Mutation produced invalid task data', {
            cause: error,
          });
        }

        await replaceFile(mutation.tasks);
        return clone(mutation.result);
      });
    },
  });
}
