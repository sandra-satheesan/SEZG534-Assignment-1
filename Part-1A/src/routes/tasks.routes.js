import { Router } from 'express';
import {
  validateCreateTask,
  validateTaskFilters,
  validateUpdateTask,
} from '../validation/tasks.validation.js';
import { createTasksController } from '../controllers/tasks.controller.js';

export function createTasksRouter(service) {
  const router = Router();
  const controller = createTasksController(service);

  router.post('/', validateCreateTask, controller.createTask);
  router.get('/', validateTaskFilters, controller.listTasks);
  router.patch('/:id', validateUpdateTask, controller.updateTask);
  router.delete('/:id', controller.deleteTask);
  router.get('/:id', controller.getTask);

  return router;
}
