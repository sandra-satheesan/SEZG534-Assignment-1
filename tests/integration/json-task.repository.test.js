import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import * as fileSystem from 'node:fs/promises';
import { createJsonTaskRepository } from '../../src/persistence/json-task.repository.js';

const validTask = {
  id: '11111111-1111-4111-8111-111111111111',
  title: 'Valid task',
  description: 'Valid details',
  priority: 'low',
  tags: [],
  status: 'pending',
};

describe('task repository persistence failures (FR-014)', () => {
  let directory;
  let filePath;

  beforeEach(async () => {
    directory = await mkdtemp(path.join(tmpdir(), 'smart-todo-persistence-'));
    filePath = path.join(directory, 'tasks.json');
  });

  afterEach(async () => {
    await rm(directory, { recursive: true, force: true });
  });

  test('initializes a new file to an empty task list', async () => {
    const repository = createJsonTaskRepository(filePath);

    await expect(repository.readAll()).resolves.toEqual([]);
    await expect(readFile(filePath, 'utf8')).resolves.toBe('[]\n');
  });

  test.each([
    ['malformed JSON', '{'],
    ['invalid stored shape', JSON.stringify([{ ...validTask, priority: 'urgent' }])],
  ])('reports %s without replacing stored bytes', async (label, contents) => {
    await writeFile(filePath, contents);
    const repository = createJsonTaskRepository(filePath);

    await expect(repository.readAll()).rejects.toMatchObject({
      status: 500,
      code: 'PERSISTENCE_ERROR',
    });
    await expect(readFile(filePath, 'utf8')).resolves.toBe(contents);
  });

  test('reports unreadable storage rather than treating it as empty', async () => {
    const readError = Object.assign(new Error('permission denied'), { code: 'EACCES' });
    const repository = createJsonTaskRepository(filePath, {
      fileSystem: { readFile: async () => { throw readError; } },
    });

    await expect(repository.readAll()).rejects.toMatchObject({
      status: 500,
      code: 'PERSISTENCE_ERROR',
    });
  });

  test('reports an unwritable store and preserves the existing canonical data', async () => {
    await writeFile(filePath, `${JSON.stringify([validTask], null, 2)}\n`);
    const fileSystemWithWriteFailure = {
      ...fileSystem,
      open: async () => {
        throw Object.assign(new Error('permission denied'), { code: 'EACCES' });
      },
    };
    const repository = createJsonTaskRepository(filePath, {
      fileSystem: fileSystemWithWriteFailure,
    });

    await expect(repository.mutate((tasks) => ({
      tasks: [...tasks],
      result: 'saved',
    }))).rejects.toMatchObject({
      status: 500,
      code: 'PERSISTENCE_ERROR',
    });
    await expect(readFile(filePath, 'utf8')).resolves.toBe(
      `${JSON.stringify([validTask], null, 2)}\n`,
    );
  });
});
