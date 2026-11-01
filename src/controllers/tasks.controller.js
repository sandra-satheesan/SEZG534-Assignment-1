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

    async updateTask(request, response) {
      const task = await service.updateTask(request.params.id, request.body);
      response.status(200).json({ data: task });
    },

    async deleteTask(request, response) {
      const result = await service.deleteTask(request.params.id);
      response.status(200).json({ data: result });
    },
  });
}
