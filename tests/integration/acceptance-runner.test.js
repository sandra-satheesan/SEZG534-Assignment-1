import { startAcceptanceServer } from '../../acceptance/run-acceptance.js';

describe('independent acceptance server helper (FR-013, FR-016)', () => {
  test('starts the real server and exposes only its public HTTP contract', async () => {
    const server = await startAcceptanceServer();

    try {
      expect(server.baseUrl).toMatch(/^http:\/\/127\.0\.0\.1:\d+$/);
      const response = await server.request('/api/not-a-route');

      expect(response.status).toBe(404);
      await expect(response.json()).resolves.toEqual({
        error: {
          code: 'NOT_FOUND',
          message: 'Route not found',
        },
      });
    } finally {
      await server.stop();
    }
  });
});
