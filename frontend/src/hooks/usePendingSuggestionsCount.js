import { useEffect, useState } from 'react';
import { suggestionsAPI } from '../services/api';

/**
 * Hook to fetch and auto-refresh pending suggestions count
 * Refreshes every 60 seconds
 */
export const usePendingSuggestionsCount = () => {
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchCount = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await suggestionsAPI.getPendingCount();
      setCount(response.data?.count || 0);
    } catch (err) {
      console.error('Error fetching pending count:', err);
      setError(err.message);
      // On error, don't update the count, keep the last value
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Fetch immediately on mount
    fetchCount();

    // Set up interval to refresh every 60 seconds
    const interval = setInterval(() => {
      fetchCount();
    }, 60000);

    // Cleanup interval on unmount
    return () => clearInterval(interval);
  }, []);

  return { count, loading, error, refetch: fetchCount };
};
