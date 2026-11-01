export const TASK_PRIORITIES = Object.freeze(['low', 'medium', 'high']);
export const TASK_STATUSES = Object.freeze(['pending', 'in-progress', 'completed']);
export const TASK_FIELDS = Object.freeze([
  'id',
  'title',
  'description',
  'priority',
  'tags',
  'status',
]);

const prioritySet = new Set(TASK_PRIORITIES);
const statusSet = new Set(TASK_STATUSES);
const taskFieldSet = new Set(TASK_FIELDS);
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function createTaskRecord(input, id) {
  return {
    id,
    title: input.title,
    description: input.description,
    priority: input.priority,
    tags: [...input.tags],
    status: 'pending',
  };
}

export function isTaskRecord(task) {
  if (
    task === null
    || typeof task !== 'object'
    || Array.isArray(task)
    || Object.keys(task).length !== TASK_FIELDS.length
    || Object.keys(task).some((field) => !taskFieldSet.has(field))
  ) {
    return false;
  }

  if (
    typeof task.id !== 'string'
    || !uuidPattern.test(task.id)
    || typeof task.title !== 'string'
    || task.title.length === 0
    || task.title.trim() !== task.title
    || typeof task.description !== 'string'
    || task.description.length === 0
    || task.description.trim() !== task.description
    || !prioritySet.has(task.priority)
    || !statusSet.has(task.status)
    || !Array.isArray(task.tags)
  ) {
    return false;
  }

  const tags = new Set();
  for (const tag of task.tags) {
    if (
      typeof tag !== 'string'
      || tag.length === 0
      || tag.trim() !== tag
      || tags.has(tag)
    ) {
      return false;
    }
    tags.add(tag);
  }

  return true;
}

export function isTaskCollection(tasks) {
  if (!Array.isArray(tasks)) {
    return false;
  }

  const ids = new Set();
  for (const task of tasks) {
    if (!isTaskRecord(task) || ids.has(task.id)) {
      return false;
    }
    ids.add(task.id);
  }

  return true;
}
