import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { positionsAPI } from '../services/api';

/**
 * Hook that fetches the positions analysis and returns a count
 * of items that need attention (missing positions).
 * Auto-refreshes every 5 minutes.
 */
export function usePositionsAttentionCount() {
  const { user } = useAuth();
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(false);

  const fetchCount = async () => {
    const municipalityId = user?.municipality_id;
    if (!municipalityId) return;

    // Get current month (YYYY-MM)
    const now = new Date();
    const month = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;

    try {
      setLoading(true);
      const res = await positionsAPI.getAnalysis(municipalityId, month);
      const data = res.data;
      if (data?.summary) {
        setCount(data.summary.positions_missing || 0);
      }
    } catch {
      // Silently fail — badge just won't show
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user?.municipality_id) {
      fetchCount();
      const interval = setInterval(fetchCount, 5 * 60 * 1000); // 5 min
      return () => clearInterval(interval);
    }
  }, [user?.municipality_id]);

  return { count, loading };
}
