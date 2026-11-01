import { Router } from 'express';
import {
  validateCreateTask,
} from '../validation/tasks.validation.js';
import { createTasksController } from '../controllers/tasks.controller.js';

export function createTasksRouter(service) {
  const router = Router();
  const controller = createTasksController(service);

  router.post('/', validateCreateTask, controller.createTask);
  router.get('/', controller.listTasks);
  router.get('/:id', controller.getTask);

  return router;
}
