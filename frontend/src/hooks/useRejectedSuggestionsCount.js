import { useState, useEffect } from 'react';
import { suggestionsAPI } from '../services/api';

/**
 * Hook to fetch and monitor count of rejected suggestions for employee
 * Auto-refreshes every 60 seconds
 */
export const useRejectedSuggestionsCount = () => {
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchCount = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await suggestionsAPI.getMyRejected();
      const rejectedSuggestions = response.data || [];
      setCount(rejectedSuggestions.length);
    } catch (err) {
      console.error('Error fetching rejected suggestions count:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCount(); // Immediate fetch on mount
    const interval = setInterval(fetchCount, 60000); // 60 second refresh
    return () => clearInterval(interval); // Cleanup on unmount
  }, []);

  return { count, loading, error, refetch: fetchCount };
};
