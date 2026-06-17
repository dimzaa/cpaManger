import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { usePendingSuggestionsCount } from '../../hooks/usePendingSuggestionsCount';

vi.mock('../../services/api', () => ({
  suggestionsAPI: {
    getPendingCount: vi.fn(),
  },
}));

import { suggestionsAPI } from '../../services/api';

describe('usePendingSuggestionsCount', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Do NOT enable fake timers globally — waitFor uses setTimeout internally
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('initializes with count=0, loading=false, error=null', () => {
    suggestionsAPI.getPendingCount.mockResolvedValue({ data: { count: 5 } });
    const { result } = renderHook(() => usePendingSuggestionsCount());
    expect(result.current.count).toBe(0);
    expect(result.current.error).toBeNull();
  });

  it('fetches count on mount', async () => {
    suggestionsAPI.getPendingCount.mockResolvedValue({ data: { count: 7 } });
    const { result } = renderHook(() => usePendingSuggestionsCount());

    await waitFor(() => {
      expect(result.current.count).toBe(7);
    });

    expect(suggestionsAPI.getPendingCount).toHaveBeenCalledTimes(1);
  });

  it('handles zero count from API', async () => {
    suggestionsAPI.getPendingCount.mockResolvedValue({ data: { count: 0 } });
    const { result } = renderHook(() => usePendingSuggestionsCount());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.count).toBe(0);
  });

  it('handles API error gracefully without crashing', async () => {
    suggestionsAPI.getPendingCount.mockRejectedValue(new Error('Network Error'));
    const { result } = renderHook(() => usePendingSuggestionsCount());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe('Network Error');
  });

  it('handles missing count field (uses 0 as default)', async () => {
    suggestionsAPI.getPendingCount.mockResolvedValue({ data: {} });
    const { result } = renderHook(() => usePendingSuggestionsCount());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.count).toBe(0);
  });

  it('exposes a refetch function', () => {
    suggestionsAPI.getPendingCount.mockResolvedValue({ data: { count: 3 } });
    const { result } = renderHook(() => usePendingSuggestionsCount());
    expect(typeof result.current.refetch).toBe('function');
  });

  it('refetch triggers another API call', async () => {
    suggestionsAPI.getPendingCount.mockResolvedValue({ data: { count: 3 } });
    const { result } = renderHook(() => usePendingSuggestionsCount());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    await act(async () => {
      await result.current.refetch();
    });

    expect(suggestionsAPI.getPendingCount).toHaveBeenCalledTimes(2);
  });

  it('polls every 60 seconds', async () => {
    vi.useFakeTimers();
    suggestionsAPI.getPendingCount.mockResolvedValue({ data: { count: 1 } });
    renderHook(() => usePendingSuggestionsCount());

    await act(async () => {
      await Promise.resolve(); // flush initial call
    });

    expect(suggestionsAPI.getPendingCount).toHaveBeenCalledTimes(1);

    await act(async () => {
      vi.advanceTimersByTime(60000);
      await Promise.resolve();
    });

    expect(suggestionsAPI.getPendingCount).toHaveBeenCalledTimes(2);
  });

  it('clears interval on unmount', async () => {
    vi.useFakeTimers();
    suggestionsAPI.getPendingCount.mockResolvedValue({ data: { count: 1 } });
    const { unmount } = renderHook(() => usePendingSuggestionsCount());

    await act(async () => {
      await Promise.resolve();
    });

    unmount();

    await act(async () => {
      vi.advanceTimersByTime(60000);
      await Promise.resolve();
    });

    // No additional calls after unmount
    expect(suggestionsAPI.getPendingCount).toHaveBeenCalledTimes(1);
  });
});
