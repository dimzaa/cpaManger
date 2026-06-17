import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import PortalWrapper from '../components/portal/PortalWrapper';
import MonthlySnapshot from '../components/portal/MonthlySnapshot';
import RetroExplainer from '../components/portal/RetroExplainer';
import { useAuth } from '../context/AuthContext';
import { budgetAPI, municipalityAPI, ministryAPI } from '../services/api';
import { formatShekel, getLast12Months, getCurrentMonth } from '../utils/format';
import { getBudgetStatus, getBudgetStatusBadge } from '../utils/budgetStatus';
import { ChevronLeft } from 'lucide-react';

export default function PortalHomePage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [budget, setBudget] = useState(null);
  const [selectedMonth, setSelectedMonth] = useState(getCurrentMonth());
  const [selectedMunicipality, setSelectedMunicipality] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [municipalitiesMap, setMunicipalitiesMap] = useState({});
  const [assignedMunicipalities, setAssignedMunicipalities] = useState([]);
  const [policyAlerts, setPolicyAlerts] = useState([]);
  const months = getLast12Months();
  const budgetStatus = budget
    ? getBudgetStatus({
        dueAmount: budget.breakdown_total,
        paidAmount: budget.invoice_total,
        month: selectedMonth,
      })
    : null;
  const statusBadge = budgetStatus ? getBudgetStatusBadge(budgetStatus.key) : null;

  // Initialize municipality selection and fetch names
  useEffect(() => {
    const initializeMunicipalities = async () => {
      try {
        // Fetch all municipalities to get names
        const allMunis = await municipalityAPI.getAll();
        const munisArray = Array.isArray(allMunis) ? allMunis : (allMunis.data || []);
        
        // Build map of ID -> Name
        const munisMap = {};
        munisArray.forEach(m => {
          munisMap[m.id] = m.name;
        });
        setMunicipalitiesMap(munisMap);

        if (user?.role === 'employee') {
          // Employee: use assigned municipalities
          const assignedMunis = user?.municipality_ids || [];
          setAssignedMunicipalities(assignedMunis);
          if (assignedMunis.length > 0 && !selectedMunicipality) {
            setSelectedMunicipality(assignedMunis[0]);
          }
        } else if (user?.municipality_id) {
          // Municipality user: use their assigned municipality
          setSelectedMunicipality(user.municipality_id);
        }
      } catch (err) {
        console.error('Error loading municipalities:', err);
      }
    };

    if (user) {
      initializeMunicipalities();
    }
  }, [user]);

  // Load policy alerts when municipality is known
  useEffect(() => {
    if (!selectedMunicipality) return;
    ministryAPI.getPolicyChanges({ municipality_id: selectedMunicipality, unacknowledged_only: true, severity: 'high' })
      .then(res => setPolicyAlerts(res.data || []))
      .catch(() => setPolicyAlerts([]));
  }, [selectedMunicipality]);

  // Load budget when selected municipality or month changes
  useEffect(() => {
    loadBudgetData();
  }, [selectedMonth, selectedMunicipality]);

  const loadBudgetData = async () => {
    if (!selectedMunicipality) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const res = await budgetAPI.getBudgetMonth(selectedMunicipality, selectedMonth);
      setBudget(res.data);
    } catch (err) {
      if (err.response?.status === 404) {
        setError('אין נתונים זמינים לחודש זה עדיין. הנתונים יופיעו לאחר שרואה החשבון יעלה את הקבצים.');
        setBudget(null);
      } else {
        setError('שגיאה בטעינת הנתונים');
        console.error('Budget load error:', err.response?.status, err.response?.data);
      }
    } finally {
      setLoading(false);
    }
  };

  const hasRetro = budget?.budget_lines?.some((line) => line.line_type === 'retro');

  return (
    <PortalWrapper title="סטטוס תקציב">
      <div className="max-w-7xl">
        {/* Policy Alerts Banner */}
        {policyAlerts.length > 0 && (
          <div className="mb-6 p-4 bg-red-50 border-2 border-red-400 rounded-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className="text-2xl">🔴</span>
              <div>
                <p className="font-hebrew font-bold text-red-800">
                  {policyAlerts.length === 1 ? 'שינוי מדיניות חשוב הדורש אישור' : `${policyAlerts.length} שינויי מדיניות חשובים הדורשים אישור`}
                </p>
                <p className="font-hebrew text-red-700 text-sm mt-0.5">{policyAlerts[0].title}</p>
              </div>
            </div>
            <button
              onClick={() => navigate('/portal/ministry')}
              className="shrink-0 px-4 py-2 bg-red-600 text-white rounded-lg font-hebrew font-medium hover:bg-red-700 transition text-sm"
            >
              צפה ואשר
            </button>
          </div>
        )}

        {/* Selectors */}
        <div className="mb-8 grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Municipality Selector for Employees */}
          {user?.role === 'employee' && assignedMunicipalities.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2 font-hebrew">בחר רשות</label>
              <select
                value={selectedMunicipality || ''}
                onChange={(e) => setSelectedMunicipality(parseInt(e.target.value))}
                className="w-full border border-neutral-300 rounded-lg px-4 py-2 font-hebrew"
              >
                {assignedMunicipalities.map((munId) => (
                  <option key={munId} value={munId}>
                    {municipalitiesMap[munId] || `ID: ${munId}`}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Month Selector */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2 font-hebrew">בחר חודש</label>
            <select
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
              className="w-full border border-neutral-300 rounded-lg px-4 py-2 font-hebrew"
            >
              {months.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        )}

        {error && (
          <div className="p-6 bg-neutral-100 border border-neutral-300 rounded-lg text-center text-neutral-700 font-hebrew mb-8">
            {error}
          </div>
        )}

        {budget && (
          <>
            {/* 3 Summary Boxes */}
            <MonthlySnapshot
              invoiceTotal={budget.invoice_total}
              breakdownTotal={budget.breakdown_total}
              difference={budget.difference}
              statusKey={budgetStatus?.key}
            />

            {/* Status Banner */}
            {statusBadge && (
              <div className={`mb-8 p-6 rounded-lg text-center font-hebrew border ${statusBadge.className}`}>
                <div className="text-lg font-bold">{statusBadge.icon} {statusBadge.text}</div>
                <div className="text-sm mt-1">
                  {budgetStatus.key === 'balanced'
                    ? 'התשלום החודשי תואם לסכום המגיע.'
                    : budgetStatus.key === 'awaiting_data'
                      ? 'ממתין לנתונים לחודש זה.'
                      : budgetStatus.key === 'current_gap'
                        ? 'יתרה פתוחה במחזור הדיווח הנוכחי.'
                        : 'נדרש בירור חשבונאי לפער זה.'}
                </div>
              </div>
            )}

            {/* Retro Explainer (only if exists) */}
            {hasRetro && <RetroExplainer />}

            {/* Quick Topic Summary Table */}
            <div className="bg-white rounded-lg shadow-md overflow-hidden mb-8">
              <div className="px-6 py-4 border-b border-neutral-200 bg-neutral-50">
                <h2 className="font-hebrew font-bold text-lg">סיכום נושאי תקציב</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-neutral-50 border-b border-neutral-200">
                    <tr className="text-right">
                      <th className="px-6 py-3 font-hebrew font-bold">נושא</th>
                      <th className="px-6 py-3 font-hebrew font-bold">סכום</th>
                      <th className="px-6 py-3 font-hebrew font-bold">סטטוס</th>
                    </tr>
                  </thead>
                  <tbody>
                    {budget.budget_lines.map((line) => {
                      let statusIcon = '✅';
                      if (line.line_type === 'retro') statusIcon = '🔄';
                      else if (line.line_type === 'shortage') statusIcon = '⚠️';
                      else if (line.line_type === 'adjustment') statusIcon = '📋';

                      return (
                        <tr
                          key={line.id}
                          className={`border-b border-neutral-200 text-right ${
                            line.line_type === 'retro'
                              ? 'bg-yellow-50'
                              : line.line_type === 'shortage'
                              ? 'bg-red-50'
                              : ''
                          }`}
                        >
                          <td className="px-6 py-3 font-medium text-neutral-900 font-hebrew">
                            {line.budget_topic}
                          </td>
                          <td className="px-6 py-3 font-medium">{formatShekel(line.amount)}</td>
                          <td className="px-6 py-3">{statusIcon}</td>
                        </tr>
                      );
                    })}
                    <tr className="border-t-2 border-neutral-300 bg-neutral-50 text-right font-bold">
                      <td className="px-6 py-3 font-hebrew">סה"כ</td>
                      <td className="px-6 py-3">{formatShekel(budget.invoice_total)}</td>
                      <td className="px-6 py-3"></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            {/* Full Detail Button */}
            <div className="text-center">
              <button
                onClick={() => navigate(`/portal/budget?month=${selectedMonth}&municipality=${selectedMunicipality}`)}
                className="inline-flex items-center gap-2 px-6 py-3 bg-primary-500 text-white rounded-lg font-medium hover:bg-primary-600 transition font-hebrew"
              >
                לפירוט מלא
                <ChevronLeft size={20} />
              </button>
            </div>
          </>
        )}
      </div>
    </PortalWrapper>
  );
}
