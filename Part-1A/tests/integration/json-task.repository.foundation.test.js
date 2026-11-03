import {
  mkdtemp,
  readFile,
  readdir,
  rm,
  stat,
  writeFile,
  mkdir,
} from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { createJsonTaskRepository } from '../../src/persistence/json-task.repository.js';

const firstTask = {
  id: '11111111-1111-4111-8111-111111111111',
  title: 'Initial task',
  description: 'Initial details',
  priority: 'medium',
  tags: ['first'],
  status: 'pending',
};

describe('JSON task repository foundation (FR-013, FR-014)', () => {
  let directory;
  let filePath;

  beforeEach(async () => {
    directory = await mkdtemp(path.join(tmpdir(), 'smart-todo-repository-'));
    filePath = path.join(directory, 'tasks.json');
  });

  afterEach(async () => {
    await rm(directory, { recursive: true, force: true });
  });

  test('initializes a missing store as an empty JSON array', async () => {
    const repository = createJsonTaskRepository(filePath);

    await expect(repository.readAll()).resolves.toEqual([]);
    await expect(readFile(filePath, 'utf8')).resolves.toBe('[]\n');
  });

  test('reports malformed JSON and invalid stored task shapes', async () => {
    await writeFile(filePath, '{invalid');
    const repository = createJsonTaskRepository(filePath);

    await expect(repository.readAll()).rejects.toMatchObject({
      code: 'PERSISTENCE_ERROR',
      status: 500,
    });
    await expect(readFile(filePath, 'utf8')).resolves.toBe('{invalid');

    await writeFile(filePath, JSON.stringify([{ ...firstTask, status: 'unknown' }]));
    await expect(repository.readAll()).rejects.toMatchObject({
      code: 'PERSISTENCE_ERROR',
      status: 500,
    });
  });

  test('reports storage read failures without converting them to an empty collection', async () => {
    const readError = Object.assign(new Error('read denied'), { code: 'EACCES' });
    const repository = createJsonTaskRepository(filePath, {
      fileSystem: { readFile: async () => { throw readError; } },
    });

    await expect(repository.readAll()).rejects.toMatchObject({
      code: 'PERSISTENCE_ERROR',
      status: 500,
    });
  });

  test('serializes concurrent mutations and persists each complete result', async () => {
    const repository = createJsonTaskRepository(filePath);
    const secondTask = { ...firstTask, id: '22222222-2222-4222-8222-222222222222' };

    await Promise.all([
      repository.mutate(async (tasks) => {
        await new Promise((resolve) => setImmediate(resolve));
        return { tasks: [...tasks, firstTask], result: firstTask.id };
      }),
      repository.mutate(async (tasks) => ({
        tasks: [...tasks, secondTask],
        result: secondTask.id,
      })),
    ]);

    await expect(repository.readAll()).resolves.toEqual([firstTask, secondTask]);
    await expect(readFile(filePath, 'utf8')).resolves.toBe(
      `${JSON.stringify([firstTask, secondTask], null, 2)}\n`,
    );
  });

  test('preserves the previous canonical file when atomic replacement fails', async () => {
    await writeFile(filePath, `${JSON.stringify([firstTask], null, 2)}\n`);
    const failingFileSystem = {
      mkdir,
      readFile,
      writeFile,
      open: (...args) => import('node:fs/promises').then((fs) => fs.open(...args)),
      unlink: (...args) => import('node:fs/promises').then((fs) => fs.unlink(...args)),
      rename: async () => {
        throw new Error('simulated replacement failure');
      },
    };
    const repository = createJsonTaskRepository(filePath, {
      fileSystem: failingFileSystem,
    });
    const secondTask = { ...firstTask, id: '22222222-2222-4222-8222-222222222222' };

    await expect(repository.mutate((tasks) => ({
      tasks: [...tasks, secondTask],
      result: secondTask.id,
    }))).rejects.toMatchObject({
      code: 'PERSISTENCE_ERROR',
      status: 500,
    });

    await expect(readFile(filePath, 'utf8')).resolves.toBe(
      `${JSON.stringify([firstTask], null, 2)}\n`,
    );
    await expect(readdir(directory)).resolves.toEqual(['tasks.json']);
  });

  test('creates persistence files with restrictive permissions', async () => {
    const repository = createJsonTaskRepository(filePath);

    await repository.readAll();

    const file = await stat(filePath);
    expect(file.mode & 0o777).toBe(0o600);
  });
});
