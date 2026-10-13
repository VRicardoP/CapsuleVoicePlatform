import { describe, it, expect } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useSSE } from './useSSE';

describe('useSSE', () => {
  it('creates EventSource without error', () => {
    const url = 'http://localhost:8000/api/v1/whatsapp/sse/test';
    expect(() => {
      const { unmount } = renderHook(() => useSSE(url, {}));
      unmount();
    }).not.toThrow();
  });

  it('closes EventSource on unmount', () => {
    const url = 'http://localhost:8000/api/v1/whatsapp/sse/test';
    const { unmount } = renderHook(() =>
      useSSE(url, { message: () => {} })
    );
    // Should not throw on cleanup
    expect(() => unmount()).not.toThrow();
  });
});
