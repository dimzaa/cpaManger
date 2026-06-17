import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../services/store';
import { budgetAPI } from '../services/api';
import { format } from 'date-fns';
import { he } from 'date-fns/locale';

export default function HistoryPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const [historyData, setHistoryData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    if (!user?.municipality_id) {
      setError('Municipality information not available');
      return;
    }

    setLoading(true);
    try {
      const response = await budgetAPI.getBudgetHistory(user.municipality_id, 12);
      setHistoryData(response.data);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load history');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8 flex justify-between items-center">
          <h1 className="text-3xl font-bold text-gray-900">📊 Budget History</h1>
          <div className="flex gap-4">
            <button
              onClick={() => navigate('/dashboard')}
              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
            >
              Back to Dashboard
            </button>
            <button
              onClick={logout}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">Loading budget history...</p>
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            <p>{error}</p>
          </div>
        ) : historyData ? (
          <div className="space-y-8">
            {Object.entries(historyData.months).map(([month, data]) => (
              <div key={month} className="bg-white rounded-lg shadow p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">
                  {format(new Date(`${month}-01`), 'MMMM yyyy', { locale: he })}
                </h2>

                <div className="grid grid-cols-3 gap-4 mb-6">
                  <div className="bg-blue-50 rounded p-4">
                    <p className="text-sm text-gray-600">Invoice Total</p>
                    <p className="text-2xl font-bold text-blue-600">
                      ₪{data.invoice_total?.toLocaleString('he-IL')}
                    </p>
                  </div>
                  <div className="bg-green-50 rounded p-4">
                    <p className="text-sm text-gray-600">Breakdown Total</p>
                    <p className="text-2xl font-bold text-green-600">
                      ₪{data.breakdown_total?.toLocaleString('he-IL')}
                    </p>
                  </div>
                  <div
                    className={`rounded p-4 ${
                      data.is_balanced ? 'bg-green-50' : 'bg-yellow-50'
                    }`}
                  >
                    <p className="text-sm text-gray-600">Status</p>
                    <p
                      className={`text-2xl font-bold ${
                        data.is_balanced ? 'text-green-600' : 'text-yellow-600'
                      }`}
                    >
                      {data.is_balanced ? '✅ Balanced' : '⚠️ Unbalanced'}
                    </p>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-100">
                      <tr>
                        <th className="px-4 py-2 text-left">Topic</th>
                        <th className="px-4 py-2 text-left">Amount</th>
                        <th className="px-4 py-2 text-left">Type</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.budget_lines.map((line, idx) => (
                        <tr key={idx} className="border-b border-gray-200 hover:bg-gray-50">
                          <td className="px-4 py-2">{line.budget_topic}</td>
                          <td className="px-4 py-2">
                            ₪{line.amount.toLocaleString('he-IL')}
                          </td>
                          <td className="px-4 py-2">
                            <span className="inline-block px-2 py-1 rounded text-xs bg-blue-100 text-blue-800">
                              {line.line_type}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        ) : null}
      </main>
    </div>
  );
}
