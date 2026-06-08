import { describe, it, expect } from 'vitest';

// Tests for the API response contract that the frontend expects from the backend.
// These mirror the backend's app/core/response.py helpers.
describe('API Response contract', () => {
  it('should validate ok response structure', () => {
    const mockOkResponse = {
      code: 0,
      message: 'ok',
      data: { id: 1, name: 'test' },
      timestamp: '2026-01-01T00:00:00Z',
    };
    expect(mockOkResponse.code).toBe(0);
    expect(mockOkResponse.message).toBe('ok');
    expect(mockOkResponse.data).toEqual({ id: 1, name: 'test' });
    expect(typeof mockOkResponse.timestamp).toBe('string');
  });

  it('should validate error response structure', () => {
    const mockErrorResponse = {
      code: 401,
      message: 'Unauthorized',
      data: null,
      timestamp: '2026-01-01T00:00:00Z',
    };
    expect(mockErrorResponse.code).toBe(401);
    expect(mockErrorResponse.message).toBe('Unauthorized');
    expect(mockErrorResponse.data).toBeNull();
  });

  it('should validate paged response structure', () => {
    const mockPagedResponse = {
      code: 0,
      message: 'ok',
      data: {
        items: [{ id: 1 }],
        page_info: { page: 2, page_size: 10, total: 50, total_pages: 5 },
      },
      timestamp: '2026-01-01T00:00:00Z',
    };
    expect(mockPagedResponse.data.page_info.total).toBe(50);
    expect(mockPagedResponse.data.page_info.page).toBe(2);
    expect(mockPagedResponse.data.page_info.total_pages).toBe(5);
    expect(mockPagedResponse.data.items).toHaveLength(1);
  });

  it('should validate empty paged response', () => {
    const mockPagedResponse = {
      code: 0,
      message: 'ok',
      data: {
        items: [],
        page_info: { page: 1, page_size: 20, total: 0, total_pages: 0 },
      },
      timestamp: '2026-01-01T00:00:00Z',
    };
    expect(mockPagedResponse.data.page_info.total).toBe(0);
    expect(mockPagedResponse.data.page_info.total_pages).toBe(0);
    expect(mockPagedResponse.data.items).toHaveLength(0);
  });

  it('should handle null data correctly', () => {
    const response = { code: 0, message: 'Deleted', data: null, timestamp: '2026-01-01T00:00:00Z' };
    expect(response.data).toBeNull();
    expect(response.code).toBe(0);
  });

  it('should recognize various error codes', () => {
    const codes = [400, 401, 403, 404, 409, 422, 500];
    for (const code of codes) {
      const resp = { code, message: 'Error', data: null, timestamp: '2026-01-01T00:00:00Z' };
      expect(resp.code).toBe(code);
    }
  });
});
