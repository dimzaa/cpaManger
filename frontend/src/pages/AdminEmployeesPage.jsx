import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { employeesAPI, municipalityAPI } from '../services/api';
import { formatShekel } from '../utils/format';

export default function AdminEmployeesPage() {
  const navigate = useNavigate();
  const [employees, setEmployees] = useState([]);
  const [municipalities, setMunicipalities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    first_name: '',
    last_name: '',
    municipality_ids: []
  });
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      console.log('🔵 Loading employees and municipalities...');
      
      const [empRes, munRes] = await Promise.all([
        employeesAPI.getAll(),
        municipalityAPI.getAll()
      ]);
      
      console.log('✅ Employees response:', empRes);
      console.log('✅ Municipalities response:', munRes);
      
      // Handle different response formats
      const employees = empRes.data || empRes || [];
      const municipalities = Array.isArray(munRes) ? munRes : (munRes.data || []);
      
      console.log('✅ Employees extracted:', employees);
      console.log('✅ Municipalities extracted:', municipalities);
      
      setEmployees(employees);
      setMunicipalities(municipalities);
    } catch (err) {
      const errorMsg = 'שגיאה בטעינת הנתונים';
      console.log('❌ Load error:', {
        message: err.message,
        status: err.response?.status,
        data: err.response?.data,
        errors: err.response?.data?.detail
      });
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleAddEmployee = async () => {
    try {
      console.log('🔵 handleAddEmployee called');
      console.log('Form data:', formData);
      
      if (!formData.email || !formData.password || !formData.first_name) {
        const msg = 'חובה למלא את כל השדות';
        console.log('❌ Validation error:', msg);
        setError(msg);
        return;
      }

      if (formData.municipality_ids.length === 0) {
        const msg = 'חובה להקצות לפחות מוניציפליטה אחת';
        console.log('❌ Municipality validation error:', msg);
        setError(msg);
        return;
      }

      setSubmitting(true);
      console.log('📤 Sending request to POST /api/employees');
      console.log('Request data:', formData);
      
      const res = await employeesAPI.create(formData);
      
      console.log('✅ Success response:', res);
      const employeeData = res.data.data || res.data || res;
      console.log('Employee data extracted:', employeeData);
      
      setSuccess('עובד נוצר בהצלחה ✅');
      // If response is wrapped in {data: {...}}, extract it, otherwise use directly
      const newEmployeeData = res.data.data || res.data || res;
      setEmployees([newEmployeeData, ...employees]);
      setFormData({
        email: '',
        password: '',
        first_name: '',
        last_name: '',
        municipality_ids: []
      });
      setShowAddForm(false);
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'שגיאה ביצירת עובד';
      console.log('❌ API Error:', {
        status: err.response?.status,
        data: err.response?.data,
        message: err.message
      });
      setError(errorMsg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleMunicipality = (munId) => {
    console.log('🔵 Toggle municipality:', munId);
    setFormData(prev => {
      const newIds = prev.municipality_ids.includes(munId)
        ? prev.municipality_ids.filter(id => id !== munId)
        : [...prev.municipality_ids, munId];
      console.log('Municipality IDs after toggle:', newIds);
      return {
        ...prev,
        municipality_ids: newIds
      };
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-gray-50">
      {/* Header */}
      <div className="sticky top-0 z-40 bg-gradient-to-r from-slate-900 to-slate-800 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white font-hebrew">👥 ניהול עובדים</h1>
            <p className="text-slate-300 font-hebrew text-sm mt-1">הוסף והקצה עובדים למוניציפליטות</p>
          </div>
          <button
            onClick={() => navigate('/dashboard')}
            className="px-4 py-2 bg-white text-slate-900 font-hebrew font-semibold rounded-lg hover:bg-slate-100 transition"
          >
            ← חזור
          </button>
        </div>
      </div>

      <main className="max-w-6xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Messages */}
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg mb-6">
            <p className="text-red-700 font-hebrew font-semibold">❌ {error}</p>
          </div>
        )}
        
        {success && (
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg mb-6">
            <p className="text-green-700 font-hebrew font-semibold">{success}</p>
          </div>
        )}

        {/* Add Employee Button */}
        <div className="mb-8">
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="px-6 py-3 bg-blue-600 text-white font-hebrew font-bold rounded-lg hover:bg-blue-700 transition"
          >
            + הוסף עובד חדש
          </button>
        </div>

        {/* Add Form */}
        {showAddForm && (
          <div className="bg-white rounded-2xl shadow-lg p-8 mb-8">
            <h2 className="text-2xl font-bold text-slate-900 font-hebrew mb-6">הוסף עובד חדש</h2>
            
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <input
                  type="email"
                  placeholder="דוא״ל"
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  className="px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
                <input
                  type="password"
                  placeholder="סיסמה"
                  value={formData.password}
                  onChange={(e) => setFormData({...formData, password: e.target.value})}
                  className="px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <input
                  type="text"
                  placeholder="שם פרטי"
                  value={formData.first_name}
                  onChange={(e) => setFormData({...formData, first_name: e.target.value})}
                  className="px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
                <input
                  type="text"
                  placeholder="שם משפחה"
                  value={formData.last_name}
                  onChange={(e) => setFormData({...formData, last_name: e.target.value})}
                  className="px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <p className="font-hebrew font-semibold text-slate-900 mb-3">הקצה מוניציפליטות ({municipalities.length} זמינות):</p>
                {municipalities.length === 0 && (
                  <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg mb-3">
                    <p className="text-yellow-700 font-hebrew text-sm">⚠️ אין מוניציפליטות זמינות לטעינה</p>
                  </div>
                )}
                <div className="space-y-2 max-h-40 overflow-y-auto border border-slate-200 rounded-lg p-3 bg-slate-50">
                  {municipalities.length > 0 ? (
                    municipalities.map(mun => (
                      <label key={mun.id} className="flex items-center gap-3 cursor-pointer p-2 hover:bg-white rounded transition">
                        <input
                          type="checkbox"
                          checked={formData.municipality_ids.includes(mun.id)}
                          onChange={() => handleToggleMunicipality(mun.id)}
                          className="w-4 h-4 accent-blue-600"
                        />
                        <span className="font-hebrew text-slate-900">{mun.name}</span>
                        <span className="text-xs text-slate-500 font-hebrew">({mun.code})</span>
                      </label>
                    ))
                  ) : (
                    <p className="text-slate-500 font-hebrew text-sm p-2">טוען מוניציפליטות...</p>
                  )}
                </div>
              </div>
            </div>

            <div className="flex gap-4 mt-6">
              <button
                onClick={handleAddEmployee}
                disabled={submitting}
                className="flex-1 px-6 py-3 bg-green-600 text-white font-hebrew font-bold rounded-lg hover:bg-green-700 transition disabled:opacity-50"
              >
                {submitting ? 'יוצר...' : '✅ צור עובד'}
              </button>
              <button
                onClick={() => {
                  setShowAddForm(false);
                  setFormData({ email: '', password: '', first_name: '', last_name: '', municipality_ids: [] });
                }}
                className="flex-1 px-6 py-3 bg-slate-300 text-slate-900 font-hebrew font-bold rounded-lg hover:bg-slate-400 transition"
              >
                ביטול
              </button>
            </div>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center py-16">
            <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        )}

        {/* Employees List */}
        {!loading && employees.length > 0 && (
          <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-100 border-b border-slate-200">
                  <tr>
                    <th className="px-6 py-4 text-right font-hebrew font-bold text-slate-900">שם</th>
                    <th className="px-6 py-4 text-right font-hebrew font-bold text-slate-900">דוא״ל</th>
                    <th className="px-6 py-4 text-right font-hebrew font-bold text-slate-900">מוניציפליטות</th>
                    <th className="px-6 py-4 text-right font-hebrew font-bold text-slate-900">הצעות</th>
                    <th className="px-6 py-4 text-right font-hebrew font-bold text-slate-900">סטטוס</th>
                  </tr>
                </thead>
                <tbody>
                  {employees.map((emp, idx) => (
                    <tr key={emp.id} className={idx % 2 === 0 ? 'bg-white' : 'bg-slate-50'}>
                      <td className="px-6 py-4 font-hebrew text-slate-900">
                        {emp.first_name} {emp.last_name}
                      </td>
                      <td className="px-6 py-4 font-hebrew text-slate-600">{emp.email}</td>
                      <td className="px-6 py-4">
                        <span className="inline-block px-3 py-1 bg-blue-100 text-blue-700 rounded-full font-hebrew text-sm font-semibold">
                          {emp.municipality_ids?.length || 0} מוניציפליטות
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="inline-block px-3 py-1 bg-purple-100 text-purple-700 rounded-full font-hebrew text-sm font-semibold">
                          {emp.suggestion_count || 0}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-block px-3 py-1 rounded-full font-hebrew text-sm font-semibold ${
                          emp.is_active
                            ? 'bg-green-100 text-green-700'
                            : 'bg-gray-100 text-gray-700'
                        }`}>
                          {emp.is_active ? '✅ פעיל' : '❌ לא פעיל'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {!loading && employees.length === 0 && (
          <div className="text-center py-12 bg-slate-50 rounded-xl border border-slate-200">
            <p className="text-lg text-slate-600 font-hebrew font-semibold">אין עובדים עדיין</p>
          </div>
        )}
      </main>
    </div>
  );
}
