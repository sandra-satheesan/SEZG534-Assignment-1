export function createTasksController(service) {
  return Object.freeze({
    async createTask(request, response) {
      const task = await service.createTask(request.body);
      response
        .location(`/api/tasks/${task.id}`)
        .status(201)
        .json({ data: task });
    },

    async listTasks(request, response) {
      const tasks = await service.listTasks();
      response.status(200).json({ data: tasks });
    },

    async getTask(request, response) {
      const task = await service.getTask(request.params.id);
      response.status(200).json({ data: task });
    },
  });
}
