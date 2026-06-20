import React, { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { budgetAPI } from '../../services/api';

/**
 * Priority-3 sparkline.
 *
 * Fetches per-month history for one (muni, topic_code) and renders a small
 * line chart. Use inside an expanded topic row, drawer, or anywhere a 12-month
 * trend belongs.
 *
 * Props:
 *   municipalityId (number, required)
 *   topicCode      (string, required)
 *   height         (number, default 60) — chart height in px
 *   showAxis       (bool, default false) — render X/Y axes
 */
export default function Sparkline({
  municipalityId,
  topicCode,
  height = 60,
  showAxis = false,
}) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    if (!municipalityId || !topicCode) return;
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        const res = await budgetAPI.getCodeHistory(municipalityId, topicCode);
        if (!cancelled) {
          const cleaned = (res.data || [])
            .map((r) => ({
              ym: r.year_month,
              amount: Number(r.amount_total || 0),
              regular: Number(r.amount_regular || 0),
            }))
            .sort((a, b) => a.ym.localeCompare(b.ym));
          setData(cleaned);
        }
      } catch (e) {
        if (!cancelled) setError(String(e?.message || e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [municipalityId, topicCode]);

  if (loading) return <div className="text-xs text-slate-400 text-center" style={{ height }}>טוען...</div>;
  if (error) return <div className="text-xs text-rose-500 text-center" style={{ height }}>שגיאה</div>;
  if (data.length === 0) return <div className="text-xs text-slate-400 text-center" style={{ height }}>אין היסטוריה</div>;

  // Detect color based on first vs last
  const first = data[0]?.amount ?? 0;
  const last = data[data.length - 1]?.amount ?? 0;
  const trendColor = last < first ? '#dc2626' : '#059669'; // rose-600 vs emerald-600

  return (
    <div style={{ height, width: '100%' }} dir="ltr">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 4, right: 4, bottom: 4, left: 4 }}>
          {showAxis && <XAxis dataKey="ym" tick={{ fontSize: 10 }} />}
          {showAxis && <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `₪${(v / 1000).toFixed(0)}K`} />}
          <Tooltip
            formatter={(v) => [`₪${Number(v).toLocaleString('he-IL', { maximumFractionDigits: 0 })}`, 'סכום']}
            labelFormatter={(l) => `חודש: ${l}`}
            contentStyle={{ fontSize: 12 }}
          />
          <Line
            type="monotone"
            dataKey="amount"
            stroke={trendColor}
            strokeWidth={2}
            dot={{ r: 2, fill: trendColor }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
