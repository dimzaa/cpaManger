import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../services/store';
import { usePendingSuggestionsCount } from '../hooks/usePendingSuggestionsCount';
import { Bell } from 'lucide-react';

export default function AdminPage() {
  const navigate = useNavigate();
  const { logout } = useAuthStore();
  const { count: pendingCount } = usePendingSuggestionsCount();

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8 flex justify-between items-center">
          <h1 className="text-3xl font-bold text-gray-900">👨‍💼 CPA Admin Dashboard</h1>
          <div className="flex gap-4">
            <button
              onClick={() => navigate('/upload')}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Upload Files
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

      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Pending Suggestions Alert */}
        {pendingCount > 0 && (
          <div className="mb-8 bg-amber-50 border-l-4 border-amber-500 rounded-lg p-6 shadow-md">
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-4">
                <Bell className="text-amber-600 flex-shrink-0 mt-1" size={24} />
                <div>
                  <h3 className="text-lg font-bold text-amber-900 font-hebrew">
                    🔔 יש {pendingCount} {pendingCount === 1 ? 'הצעת הסבר' : 'הצעות הסבר'} ממתינה לאישורך
                  </h3>
                  <p className="text-amber-700 font-hebrew text-sm mt-1">
                    עובדים הציעו הסברים חדשים שדורשים בדיקה ואישור
                  </p>
                </div>
              </div>
              <button
                onClick={() => navigate('/admin/approvals')}
                className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg font-hebrew font-semibold transition-colors whitespace-nowrap ml-4"
              >
                עבור לאישורים ←
              </button>
            </div>
          </div>
        )}

        <div className="bg-white rounded-lg shadow p-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">System Overview</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-blue-50 rounded-lg p-6">
              <p className="text-gray-600">Total Municipalities</p>
              <p className="text-4xl font-bold text-blue-600">3</p>
            </div>
            <div className="bg-green-50 rounded-lg p-6">
              <p className="text-gray-600">Active Runs</p>
              <p className="text-4xl font-bold text-green-600">9</p>
            </div>
            <div className="bg-yellow-50 rounded-lg p-6">
              <p className="text-gray-600">Unbalanced</p>
              <p className="text-4xl font-bold text-yellow-600">0</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
