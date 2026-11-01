import express from 'express';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { NotFoundError } from './errors/app-error.js';
import { errorHandler } from './middleware/error-handler.js';
import { createJsonTaskRepository } from './persistence/json-task.repository.js';

const DEFAULT_TASKS_FILE = fileURLToPath(new URL('../data/tasks.json', import.meta.url));

export function createApp({
  repository,
  logger = console,
  tasksFile = process.env.TASKS_FILE ?? DEFAULT_TASKS_FILE,
} = {}) {
  const taskRepository = repository ?? createJsonTaskRepository(path.resolve(tasksFile));
  const app = express();

  app.disable('x-powered-by');
  app.locals.repository = taskRepository;
  app.locals.logger = logger;
  app.use(express.json({ limit: 10_240, strict: true }));
  app.use((request, response, next) => {
    next(new NotFoundError('Route not found'));
  });
  app.use(errorHandler({ logger }));

  return app;
}
