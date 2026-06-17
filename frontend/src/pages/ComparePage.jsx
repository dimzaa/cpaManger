import React, { useEffect, useState } from 'react';
import PageWrapper from '../components/layout/PageWrapper';
import { budgetAPI, municipalityAPI } from '../services/api';
import { formatShekel as formatShekelByMode, getRoundingDisclosureText, resolveConcreteMode } from '../utils/formatShekel';
import { useRoundingMode } from '../utils/roundingMode';
import RoundingModeToggle from '../components/common/RoundingModeToggle';
import RoundingDisclosureBanner from '../components/common/RoundingDisclosureBanner';
import ShekelAmount from '../components/common/ShekelAmount';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export default function ComparePage() {
  const [municipalities, setMunicipalities] = useState([]);
  const [selectedMunicipality, setSelectedMunicipality] = useState('');
  const [month1, setMonth1] = useState('');
  const [month2, setMonth2] = useState('');
  const [comparisons, setComparisons] = useState([]);
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [roundingMode, setRoundingMode] = useRoundingMode();

  // Load municipalities on mount
  useEffect(() => {
    loadMunicipalities();
  }, []);

  // Load budget data when municipality or months change
  useEffect(() => {
    if (selectedMunicipality && month1 && month2) {
      loadComparison();
    }
  }, [selectedMunicipality, month1, month2]);

  const loadMunicipalities = async () => {
    try {
      const res = await municipalityAPI.getAll();
      setMunicipalities(res.data);
      if (res.data.length > 0) setSelectedMunicipality(res.data[0].id);
    } catch (err) {
      setError('שגיאה בטעינת העיריות');
    } finally {
      setLoading(false);
    }
  };

  const loadComparison = async () => {
    try {
      setLoading(true);
      const [budget1, budget2] = await Promise.all([
        budgetAPI.getBudgetMonth(selectedMunicipality, month1),
        budgetAPI.getBudgetMonth(selectedMunicipality, month2),
      ]);

      const comparison = [];
      const chartData = [];

      budget1.data.budget_lines.forEach((line1) => {
        const line2 = budget2.data.budget_lines.find((l) => l.id === line1.id);
        const item = {
          id: line1.id,
          topic: line1.budget_topic,
          month1: line1.amount,
          month2: line2?.amount || 0,
          difference: (line2?.amount || 0) - line1.amount,
        };
        comparison.push(item);
        chartData.push({
          topic: line1.budget_topic,
          [month1]: line1.amount,
          [month2]: line2?.amount || 0,
        });
      });

      setComparisons(comparison);
      setChartData(chartData);
    } catch (err) {
      setError('שגיאה בהשוואה');
    } finally {
      setLoading(false);
    }
  };

  const pageAmounts = [
    ...comparisons.flatMap((comp) => [comp.month1, comp.month2, comp.difference]),
    ...chartData.flatMap((row) => [row[month1], row[month2]]),
  ];
  const concreteRoundingMode = resolveConcreteMode(roundingMode, pageAmounts);
  const disclosureText = getRoundingDisclosureText(concreteRoundingMode);
  const formatShekelText = (value) => formatShekelByMode(value, { mode: concreteRoundingMode });

  return (
    <PageWrapper title="השוואת חודשים">
      <div className="space-y-6">
        <div className="bg-white p-4 rounded-lg border border-slate-200 flex items-center justify-between gap-3 flex-wrap" dir="rtl">
          <RoundingModeToggle mode={roundingMode} onChange={setRoundingMode} />
        </div>
        <RoundingDisclosureBanner text={disclosureText} />

        {/* Filters */}
        <div className="bg-white p-6 rounded-lg border border-neutral-200 grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">עיריה</label>
            <select
              value={selectedMunicipality}
              onChange={(e) => setSelectedMunicipality(e.target.value)}
              className="w-full border border-neutral-300 rounded px-4 py-2"
            >
              {municipalities.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">חודש 1</label>
            <input
              type="month"
              value={month1}
              onChange={(e) => setMonth1(e.target.value)}
              className="w-full border border-neutral-300 rounded px-4 py-2"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">חודש 2</label>
            <input
              type="month"
              value={month2}
              onChange={(e) => setMonth2(e.target.value)}
              className="w-full border border-neutral-300 rounded px-4 py-2"
            />
          </div>
        </div>

        {loading && <div className="text-center py-8"><div className="animate-spin inline-block w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full"></div></div>}
        
        {error && <div className="p-4 bg-danger/10 border border-danger text-danger rounded-lg">{error}</div>}

        {/* Comparison Table */}
        {comparisons.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-neutral-200">
              <h2 className="font-hebrew font-bold text-lg">השוואת סכומים</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-neutral-50 border-b border-neutral-200">
                  <tr>
                    <th className="px-6 py-3 text-right">נושא תקציב</th>
                    <th className="px-6 py-3 text-right">{month1}</th>
                    <th className="px-6 py-3 text-right">{month2}</th>
                    <th className="px-6 py-3 text-right">הפרש</th>
                  </tr>
                </thead>
                <tbody>
                  {comparisons.map((comp) => (
                    <tr key={comp.id} className="border-b border-neutral-200">
                      <td className="px-6 py-3 font-medium">{comp.topic}</td>
                      <td className="px-6 py-3"><ShekelAmount amount={comp.month1} mode={concreteRoundingMode} /></td>
                      <td className="px-6 py-3"><ShekelAmount amount={comp.month2} mode={concreteRoundingMode} /></td>
                      <td className={`px-6 py-3 font-medium ${comp.difference > 0 ? 'text-success' : comp.difference < 0 ? 'text-danger' : ''}`}>
                        <ShekelAmount amount={comp.difference} mode={concreteRoundingMode} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Comparison Chart */}
        {chartData.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="font-hebrew font-bold text-lg mb-4">גרף השוואה</h2>
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="topic" />
                <YAxis />
                <Tooltip formatter={(value) => formatShekelText(value)} />
                <Legend />
                <Bar dataKey={month1} fill="#1E3A5F" />
                <Bar dataKey={month2} fill="#2E5491" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </PageWrapper>
  );
}
