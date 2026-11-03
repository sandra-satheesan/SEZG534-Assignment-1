const API_BASE = '/api/tasks';

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...(options.body ? { 'content-type': 'application/json' } : {}),
      ...options.headers,
    },
  });

  let body;
  try {
    body = await response.json();
  } catch {
    throw new Error('The task service returned an unreadable response.');
  }

  if (!response.ok) {
    const error = new Error(
      body?.error?.message ?? `The request failed with status ${response.status}.`,
    );
    error.code = body?.error?.code;
    error.status = response.status;
    throw error;
  }

  return body;
}

export async function listTasks(filters = {}) {
  const query = new URLSearchParams();
  if (filters.status) query.set('status', filters.status);
  if (filters.priority) query.set('priority', filters.priority);
  if (filters.sort) query.set('sort', filters.sort);
  for (const tag of filters.tags ?? []) {
    query.append('tag', tag);
  }

  const suffix = query.size > 0 ? `?${query.toString()}` : '';
  const result = await request(`${API_BASE}${suffix}`);
  return result.data;
}

export async function getTask(id) {
  const result = await request(`${API_BASE}/${encodeURIComponent(id)}`);
  return result.data;
}

export async function createTask(task) {
  const result = await request(API_BASE, {
    method: 'POST',
    body: JSON.stringify(task),
  });
  return result.data;
}

export async function updateTask(id, changes) {
  const result = await request(`${API_BASE}/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(changes),
  });
  return result.data;
}

export async function deleteTask(id) {
  const result = await request(`${API_BASE}/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  });
  return result.data;
}
