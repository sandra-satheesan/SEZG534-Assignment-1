import express from 'express';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { NotFoundError } from './errors/app-error.js';
import { errorHandler } from './middleware/error-handler.js';
import { createJsonTaskRepository } from './persistence/json-task.repository.js';
import { createTaskService } from './services/tasks.service.js';
import { createTasksRouter } from './routes/tasks.routes.js';

const DEFAULT_TASKS_FILE = fileURLToPath(new URL('../data/tasks.json', import.meta.url));

export function createApp({
  repository,
  service,
  logger = console,
  tasksFile = process.env.TASKS_FILE ?? DEFAULT_TASKS_FILE,
} = {}) {
  const taskRepository = repository ?? createJsonTaskRepository(path.resolve(tasksFile));
  const taskService = service ?? createTaskService({ repository: taskRepository });
  const app = express();

  app.disable('x-powered-by');
  app.locals.repository = taskRepository;
  app.locals.service = taskService;
  app.locals.logger = logger;
  app.use(express.json({ limit: 10_240, strict: true }));
  app.use('/api/tasks', createTasksRouter(taskService));
  app.use((request, response, next) => {
    next(new NotFoundError('Route not found'));
  });
  app.use(errorHandler({ logger }));

  return app;
}
