import { ValidationError } from '../errors/app-error.js';
import { TASK_PRIORITIES, TASK_STATUSES } from '../models/task.js';

const PRIORITIES = new Set(TASK_PRIORITIES);
const STATUSES = new Set(TASK_STATUSES);
const CREATE_FIELDS = new Set(['title', 'description', 'priority', 'tags', 'status']);
const UPDATE_FIELDS = new Set(['title', 'description', 'priority', 'tags', 'status']);
const TASK_FILTER_FIELDS = new Set(['status', 'priority', 'tag', 'sort']);

function requireObject(body) {
  if (body === null || typeof body !== 'object' || Array.isArray(body)) {
    throw new ValidationError('Request body must be a JSON object');
  }
}

function rejectUnknownFields(body, allowedFields) {
  const unknownFields = Object.keys(body).filter((field) => !allowedFields.has(field));
  if (unknownFields.length > 0) {
    throw new ValidationError(`Unknown request property: ${unknownFields.join(', ')}`);
  }
}

function normalizeText(body, field, { required = false } = {}) {
  if (!Object.hasOwn(body, field)) {
    if (required) {
      throw new ValidationError(`${field} is required`);
    }
    return;
  }

  if (typeof body[field] !== 'string') {
    throw new ValidationError(`${field} must be a string`);
  }

  body[field] = body[field].trim();
  if (body[field].length === 0) {
    throw new ValidationError(`${field} must not be empty`);
  }
}

function validatePriority(body) {
  if (!PRIORITIES.has(body.priority)) {
    throw new ValidationError('priority must be low, medium, or high');
  }
}

function normalizeTags(body) {
  if (!Object.hasOwn(body, 'tags')) {
    throw new ValidationError('tags is required');
  }
  if (!Array.isArray(body.tags)) {
    throw new ValidationError('tags must be an array of strings');
  }

  const normalizedTags = [];
  const seen = new Set();
  for (const tag of body.tags) {
    if (typeof tag !== 'string' || tag.trim().length === 0) {
      throw new ValidationError('tags must contain only non-empty strings');
    }

    const normalizedTag = tag.trim();
    if (!seen.has(normalizedTag)) {
      seen.add(normalizedTag);
      normalizedTags.push(normalizedTag);
    }
  }

  body.tags = normalizedTags;
}

function middleware(validate) {
  return (request, response, next) => {
    try {
      requireObject(request.body);
      validate(request.body);
      next();
    } catch (error) {
      next(error);
    }
  };
}

export const validateCreateTask = middleware((body) => {
  rejectUnknownFields(body, CREATE_FIELDS);
  normalizeText(body, 'title', { required: true });
  normalizeText(body, 'description', { required: true });
  validatePriority(body);
  normalizeTags(body);

  if (Object.hasOwn(body, 'status') && body.status !== 'pending') {
    throw new ValidationError('status must be pending when creating a task');
  }
});

export const validateUpdateTask = middleware((body) => {
  rejectUnknownFields(body, UPDATE_FIELDS);
  if (Object.keys(body).length === 0) {
    throw new ValidationError('An update must contain at least one field');
  }

  normalizeText(body, 'title');
  normalizeText(body, 'description');
  if (Object.hasOwn(body, 'priority')) {
    validatePriority(body);
  }
  if (Object.hasOwn(body, 'tags')) {
    normalizeTags(body);
  }
  if (Object.hasOwn(body, 'status') && !STATUSES.has(body.status)) {
    throw new ValidationError('status must be pending, in-progress, or completed');
  }
});

function requireQueryValue(query, field, allowedValues) {
  const value = query[field];
  if (value === undefined) {
    return undefined;
  }
  if (typeof value !== 'string' || !allowedValues.has(value)) {
    throw new ValidationError(`${field} has an invalid value`);
  }
  return value;
}

export function validateTaskFilters(request, response, next) {
  try {
    const query = request.query;
    const unknownFields = Object.keys(query)
      .filter((field) => !TASK_FILTER_FIELDS.has(field));
    if (unknownFields.length > 0) {
      throw new ValidationError(`Unknown query parameter: ${unknownFields.join(', ')}`);
    }

    const status = requireQueryValue(query, 'status', STATUSES);
    const priority = requireQueryValue(query, 'priority', PRIORITIES);
    const sort = requireQueryValue(query, 'sort', new Set(['priority']));
    const rawTags = query.tag === undefined
      ? []
      : Array.isArray(query.tag) ? query.tag : [query.tag];
    const tags = [];
    const seenTags = new Set();

    for (const tag of rawTags) {
      if (typeof tag !== 'string' || tag.trim().length === 0) {
        throw new ValidationError('tag query parameters must be non-empty strings');
      }

      const normalizedTag = tag.trim();
      if (!seenTags.has(normalizedTag)) {
        seenTags.add(normalizedTag);
        tags.push(normalizedTag);
      }
    }

    request.taskFilters = {
      ...(status === undefined ? {} : { status }),
      ...(priority === undefined ? {} : { priority }),
      ...(tags.length === 0 ? {} : { tags }),
      ...(sort === undefined ? {} : { sort }),
    };
    next();
  } catch (error) {
    next(error);
  }
}
