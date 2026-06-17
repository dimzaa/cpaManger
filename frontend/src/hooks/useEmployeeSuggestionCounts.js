import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { suggestionsAPI } from '../services/api';

/**
 * Fetches the current employee's suggestion counts by status.
 * Auto-refreshes every 60 seconds.
 * Returns { pending, approved, rejected, loading }
 */
export function useEmployeeSuggestionCounts() {
  const { user } = useAuth();
  const [counts, setCounts] = useState({ pending: 0, approved: 0, rejected: 0 });
  const [loading, setLoading] = useState(false);

  const fetchCounts = async () => {
    if (user?.role !== 'employee') return;
    try {
      setLoading(true);
      const res = await suggestionsAPI.getMyCounts();
      setCounts(res.data || { pending: 0, approved: 0, rejected: 0 });
    } catch {
      // Silently fail — badges just won't show
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user?.role === 'employee') {
      fetchCounts();
      const interval = setInterval(fetchCounts, 60_000);
      return () => clearInterval(interval);
    }
  }, [user?.role, user?.id]);

  return { ...counts, loading };
}
