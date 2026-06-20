import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import PageWrapper from '../components/layout/PageWrapper';
import SmartExplanationDisplay from '../components/portal/SmartExplanationDisplay';
import ExplanationEditModal from '../components/admin/ExplanationEditModal';
import { budgetAPI, explanationsAPI, reportsAPI, ministryAPI, analyticsAPI } from '../services/api';
import { runsAPI } from '../services/api';
import { formatHebrewDate, getLast12Months } from '../utils/format';
import { formatShekel as formatShekelByMode, getRoundingDisclosureText, resolveConcreteMode, ROUNDING_MODES } from '../utils/formatShekel';
import { buildRetroSchoolYearGroups, formatEffectiveMonth } from '../utils/schoolYear';
import { generateChangeExplanation, ChangeExplanationBox } from '../utils/changeExplanations.jsx';
import { getBudgetStatus, getBudgetStatusBadge } from '../utils/budgetStatus';
import ReviewStatusControl from '../components/review/ReviewStatusControl';
import { ArrowRight } from 'lucide-react';
import { useRoundingMode } from '../utils/roundingMode';
import RoundingModeToggle from '../components/common/RoundingModeToggle';
import RoundingDisclosureBanner from '../components/common/RoundingDisclosureBanner';
import ShekelAmount from '../components/common/ShekelAmount';
import Sparkline from '../components/common/Sparkline';
import StudentCountDeltaChip from '../components/common/StudentCountDeltaChip';
import CpaInsightsPanel from '../components/common/CpaInsightsPanel';

/**
 * AdminBudgetDetailPage - Full budget detail for CPA admin
 * Same layout as PortalBudgetPage with edit controls
 */
export default function AdminBudgetDetailPage() {
  const navigate = useNavigate();
  const { id } = useParams();
  const params = new URLSearchParams(window.location.search);
  const initialMonth = params.get('month');
  const months = getLast12Months();

  console.log('📋 [AdminBudgetDetailPage] Loaded with params:', {
    municipalityId: id,
    initialMonth: initialMonth
  });

  const [budget, setBudget] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [explanations, setExplanations] = useState({});
  const [smartExplanations, setSmartExplanations] = useState({});
  const [selectedMonth, setSelectedMonth] = useState(initialMonth || '');
  const [expandedGroups, setExpandedGroups] = useState({});
  const [expandedCategories, setExpandedCategories] = useState({});
  const [expandedRetroSchoolYears, setExpandedRetroSchoolYears] = useState({});
  const [editingTopicCode, setEditingTopicCode] = useState(null);
  const [editingTopicName, setEditingTopicName] = useState(null);
  const [pdfGenerating, setPdfGenerating] = useState(false);
  const [pdfJobId, setPdfJobId] = useState(null);
  const [pdfToast, setPdfToast] = useState(null);
  const [ministryCodeCategory, setMinistryCodeCategory] = useState(new Map());
  const [institutionByTopic, setInstitutionByTopic] = useState({});
  const [topicLinesDetail, setTopicLinesDetail] = useState({}); // Phase 3.1: per-topic raw lines drill-down
  const [formulaDrivers, setFormulaDrivers] = useState({}); // Phase 3.2: per-topic formula-variance drivers
  const [transportAudit, setTransportAudit] = useState({}); // Phase 3.3: per-transport-topic route-level audit
  const [allHighSchoolBreakdown, setAllHighSchoolBreakdown] = useState({ loading: false, error: null, data: null, expanded: false });
  const [studentCountDeltas, setStudentCountDeltas] = useState({});
  const [onlyStudentCountChanges, setOnlyStudentCountChanges] = useState(false);
  const [roundingMode, setRoundingMode] = useRoundingMode();
  const pdfPollRef = React.useRef(null);

  // Clean up PDF poll on unmount
  React.useEffect(() => () => { if (pdfPollRef.current) clearInterval(pdfPollRef.current); }, []);

  useEffect(() => {
    if (selectedMonth && id) {
      loadData();
    }
  }, [selectedMonth, id]);

  const loadData = async () => {
    if (!selectedMonth) return;

    try {
      setLoading(true);
      setError(null);

      console.log(`[AdminBudgetDetailPage] Loading: municipality=${id}, month=${selectedMonth}`);

      // Load budget
      const budgetRes = await budgetAPI.getBudgetMonth(id, selectedMonth);
      setBudget(budgetRes.data);
      console.log('[AdminBudgetDetailPage] Budget loaded');

      // Load student-count deltas (best-effort; no fatal error if missing)
      try {
        if (budgetRes.data?.run_id) {
          const deltasRes = await budgetAPI.getStudentCountDeltas(budgetRes.data.run_id, Number(id));
          const deltaMap = {};
          (deltasRes.data?.lines || []).forEach((row) => {
            if (row.topic_code) deltaMap[String(row.topic_code)] = row;
          });
          setStudentCountDeltas(deltaMap);
        } else {
          setStudentCountDeltas({});
        }
      } catch (deltaErr) {
        console.warn('[AdminBudgetDetailPage] student-count deltas unavailable', deltaErr);
        setStudentCountDeltas({});
      }

      // Load ministry codes with categories
      try {
        const codesRes = await ministryAPI.getCodes();
        const categoryMap = new Map((codesRes.data || []).map(c => [String(c.code), c.category || 'כללי']));
        setMinistryCodeCategory(categoryMap);
      } catch {
        setMinistryCodeCategory(new Map());
      }

      // Load explanations
      try {
        const expRes = await explanationsAPI.getMonthExplanations(id, selectedMonth);
        const expMap = {};
        let expData = expRes.data;
        
        if (expData && typeof expData === 'object') {
          if (Array.isArray(expData.explanations)) {
            expData.explanations.forEach(exp => {
              // The API returns "explanation" field with the actual text
              if (exp.topic_code && exp.explanation) {
                expMap[exp.topic_code] = exp.explanation;
              }
            });
          } else if (!Array.isArray(expData)) {
            // For other response formats
            Object.keys(expData).forEach(topicCode => {
              if (expData[topicCode] && typeof expData[topicCode] === 'object') {
                expMap[topicCode] = expData[topicCode].explanation || expData[topicCode].custom_text || expData[topicCode];
              } else if (typeof expData[topicCode] === 'string') {
                expMap[topicCode] = expData[topicCode];
              }
            });
          }
        }
        
        setExplanations(expMap);
        console.log('[AdminBudgetDetailPage] Explanations loaded:', expMap);
      } catch (err) {
        console.error('[AdminBudgetDetailPage] Error loading explanations:', err);
        setExplanations({});
      }
    } catch (err) {
      console.error('[AdminBudgetDetailPage] Error:', err);
      setError(`שגיאה בטעינת הנתונים: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleGeneratePdf = async () => {
    if (!id || !selectedMonth) return;
    setPdfGenerating(true);
    setPdfToast({ type: 'info', msg: '⏳ מייצר דוח PDF...' });
    try {
      const res = await reportsAPI.generate(id, selectedMonth);
      const jobId = res.data.job_id;
      if (pdfPollRef.current) clearInterval(pdfPollRef.current);
      pdfPollRef.current = setInterval(async () => {
        try {
          const sr = await reportsAPI.getStatus(jobId);
          const job = sr.data;
          if (job.status === 'done') {
            clearInterval(pdfPollRef.current);
            setPdfGenerating(false);
            setPdfToast({ type: 'success', msg: '✅ הדוח מוכן — מוריד...' });
            // auto-download
            const dr = await reportsAPI.download(job.report_id);
            const blob = new Blob([dr.data], { type: 'application/pdf' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = `report_${job.report_id}.pdf`;
            document.body.appendChild(a); a.click(); a.remove();
            window.URL.revokeObjectURL(url);
            setTimeout(() => setPdfToast(null), 3000);
          } else if (job.status === 'error') {
            clearInterval(pdfPollRef.current);
            setPdfGenerating(false);
            setPdfToast({ type: 'error', msg: `❌ ${job.error || 'שגיאה בייצור'}` });
            setTimeout(() => setPdfToast(null), 4000);
          }
        } catch { clearInterval(pdfPollRef.current); setPdfGenerating(false); }
      }, 1500);
    } catch (err) {
      setPdfGenerating(false);
      setPdfToast({ type: 'error', msg: err.response?.data?.detail || '❌ שגיאה ביצירת הדוח' });
      setTimeout(() => setPdfToast(null), 4000);
    }
  };

  const handleBack = () => {
    navigate(`/municipality/${id}`);
  };

  const toggleTopicInstitutionBreakdown = async (topicCode) => {
    const current = institutionByTopic[topicCode];
    if (current?.expanded) {
      setInstitutionByTopic((prev) => ({ ...prev, [topicCode]: { ...current, expanded: false } }));
      return;
    }
    if (current?.data) {
      setInstitutionByTopic((prev) => ({ ...prev, [topicCode]: { ...current, expanded: true } }));
      return;
    }

    setInstitutionByTopic((prev) => ({ ...prev, [topicCode]: { loading: true, error: null, data: null, expanded: true } }));
    try {
      const res = await budgetAPI.getTopicInstitutions(budget.run_id, Number(id), topicCode);
      setInstitutionByTopic((prev) => ({ ...prev, [topicCode]: { loading: false, error: null, data: res.data, expanded: true } }));
    } catch (err) {
      const isMissing = err?.response?.status === 404;
      setInstitutionByTopic((prev) => ({
        ...prev,
        [topicCode]: {
          loading: false,
          error: isMissing ? 'אין פירוט לפי מוסד לריצה זו' : 'שגיאה בטעינת פירוט לפי מוסד',
          data: null,
          expanded: true,
        },
      }));
    }
  };

  // Phase 3.1: lazy-load per-line detail for one topic (gy/sharatim/mutavim/...)
  const toggleTopicLinesDetail = async (topicCode) => {
    const current = topicLinesDetail[topicCode];
    if (current?.expanded) {
      setTopicLinesDetail((prev) => ({
        ...prev,
        [topicCode]: { ...current, expanded: false },
      }));
      return;
    }
    if (current?.data) {
      setTopicLinesDetail((prev) => ({
        ...prev,
        [topicCode]: { ...current, expanded: true },
      }));
      return;
    }
    setTopicLinesDetail((prev) => ({
      ...prev,
      [topicCode]: { loading: true, error: null, data: null, expanded: true },
    }));
    try {
      const res = await budgetAPI.getTopicLines(budget.run_id, Number(id), topicCode);
      setTopicLinesDetail((prev) => ({
        ...prev,
        [topicCode]: { loading: false, error: null, data: res.data, expanded: true },
      }));
    } catch (err) {
      const isMissing = err?.response?.status === 404;
      setTopicLinesDetail((prev) => ({
        ...prev,
        [topicCode]: {
          loading: false,
          error: isMissing ? 'אין שורות פירוט לנושא זה' : 'שגיאה בטעינת פירוט שורות',
          data: null,
          expanded: true,
        },
      }));
    }
  };

  // Phase 3.2: lazy-load formula-variance drivers for one topic.
  const toggleFormulaDrivers = async (topicCode) => {
    const current = formulaDrivers[topicCode];
    if (current?.expanded) {
      setFormulaDrivers((prev) => ({
        ...prev,
        [topicCode]: { ...current, expanded: false },
      }));
      return;
    }
    if (current?.data) {
      setFormulaDrivers((prev) => ({
        ...prev,
        [topicCode]: { ...current, expanded: true },
      }));
      return;
    }
    setFormulaDrivers((prev) => ({
      ...prev,
      [topicCode]: { loading: true, error: null, data: null, expanded: true },
    }));
    try {
      const res = await analyticsAPI.getFormulaDrivers(budget.run_id, topicCode);
      setFormulaDrivers((prev) => ({
        ...prev,
        [topicCode]: { loading: false, error: null, data: res.data, expanded: true },
      }));
    } catch (err) {
      const isMissing = err?.response?.status === 404;
      setFormulaDrivers((prev) => ({
        ...prev,
        [topicCode]: {
          loading: false,
          error: isMissing ? 'אין נתוני הקשר לנושא זה' : 'שגיאה בטעינת מניעי נוסחה',
          data: null,
          expanded: true,
        },
      }));
    }
  };

  // Phase 3.3: lazy-load per-route transport audit (topics 52/140 only).
  const toggleTransportAudit = async (topicCode) => {
    const current = transportAudit[topicCode];
    if (current?.expanded) {
      setTransportAudit((prev) => ({
        ...prev,
        [topicCode]: { ...current, expanded: false },
      }));
      return;
    }
    if (current?.data) {
      setTransportAudit((prev) => ({
        ...prev,
        [topicCode]: { ...current, expanded: true },
      }));
      return;
    }
    setTransportAudit((prev) => ({
      ...prev,
      [topicCode]: { loading: true, error: null, data: null, expanded: true },
    }));
    try {
      const res = await analyticsAPI.getTransportRoutes(budget.run_id, topicCode);
      setTransportAudit((prev) => ({
        ...prev,
        [topicCode]: { loading: false, error: null, data: res.data, expanded: true },
      }));
    } catch (err) {
      const isMissing = err?.response?.status === 404;
      const isBad = err?.response?.status === 400;
      setTransportAudit((prev) => ({
        ...prev,
        [topicCode]: {
          loading: false,
          error: isMissing
            ? 'אין נתוני מסלולים לריצה זו'
            : isBad
              ? 'נתוני מסלולים זמינים רק לקודי הסעה'
              : 'שגיאה בטעינת נתוני מסלולים',
          data: null,
          expanded: true,
        },
      }));
    }
  };

  const toggleAllHighSchoolBreakdown = async () => {
    if (allHighSchoolBreakdown.expanded) {
      setAllHighSchoolBreakdown((prev) => ({ ...prev, expanded: false }));
      return;
    }
    if (allHighSchoolBreakdown.data) {
      setAllHighSchoolBreakdown((prev) => ({ ...prev, expanded: true }));
      return;
    }
    setAllHighSchoolBreakdown({ loading: true, error: null, data: null, expanded: true });
    try {
      const res = await budgetAPI.getHighSchoolBreakdown(budget.run_id, Number(id));
      setAllHighSchoolBreakdown({ loading: false, error: null, data: res.data, expanded: true });
    } catch (err) {
      const isMissing = err?.response?.status === 404;
      setAllHighSchoolBreakdown({
        loading: false,
        error: isMissing ? 'אין פירוט לפי מוסד לריצה זו' : 'שגיאה בטעינת פירוט לפי מוסד',
        data: null,
        expanded: true,
      });
    }
  };

  const handlePersistReviewStatus = async ({ status, note }) => {
    if (!budget?.run_id) {
      throw new Error('run_id חסר בנתוני התקציב');
    }

    const res = await runsAPI.updateReviewStatus(budget.run_id, status, note || '');
    const updated = res.data || {};

    setBudget((prev) => ({
      ...prev,
      review_status: updated.review_status || prev.review_status,
      review_status_note: updated.review_status_note,
      reviewed_at: updated.reviewed_at,
      reviewed_by_user_id: updated.reviewed_by_user_id,
      reviewed_by_name: updated.reviewer_name || prev.reviewed_by_name,
    }));

    return {
      reviewed_at: updated.reviewed_at,
      reviewed_by_name: updated.reviewer_name,
      review_status_note: updated.review_status_note,
    };
  };

  const toggleGroupExpanded = (groupCode) => {
    setExpandedGroups(prev => ({
      ...prev,
      [groupCode]: !prev[groupCode]
    }));
  };

  const toggleCategoryExpanded = (categoryName) => {
    setExpandedCategories(prev => ({
      ...prev,
      [categoryName]: !prev[categoryName]
    }));
  };

  const toggleSchoolYearExpanded = (schoolYearKey) => {
    setExpandedRetroSchoolYears((prev) => ({
      ...prev,
      [schoolYearKey]: !prev[schoolYearKey],
    }));
  };

  const handleExplanationModalClose = () => {
    console.log('🔒 [AdminBudgetDetailPage] Modal closing');
    setEditingTopicCode(null);
    setEditingTopicName(null);
  };

  const handleExplanationSave = (newExplanation) => {
    console.log('💾 [AdminBudgetDetailPage] Explanation saved:', {
      topicCode: editingTopicCode,
      explanation: newExplanation.substring(0, 50) + '...'
    });
    // Update the explanations state with the new explanation
    setExplanations(prev => ({
      ...prev,
      [editingTopicCode]: newExplanation
    }));
    handleExplanationModalClose();
  };

  // HELPER FUNCTIONS FOR DATA PREPARATION

  const filterActiveLines = (lines) => {
    return lines.filter(line => line.amount !== 0);
  };

  const groupByTopicCode = (lines) => {
    const grouped = {};
    lines.forEach(line => {
      const code = line.topic_code;
      if (!grouped[code]) {
        grouped[code] = [];
      }
      grouped[code].push(line);
    });
    return grouped;
  };

  const getGroupColor = (lines) => {
    const hasRetro = lines.some(l => l.is_retro || l.line_type === 'retro');
    const hasNegative = lines.some(l => l.amount < 0);
    
    if (hasRetro) return { bg: 'bg-amber-50', border: 'border-l-4 border-amber-400', badge: '🟡' };
    if (hasNegative) return { bg: 'bg-red-50', border: 'border-l-4 border-red-400', badge: '🔴' };
    return { bg: 'bg-green-50', border: 'border-l-4 border-green-400', badge: '🟢' };
  };

  const getLineColor = (line) => {
    if (line.is_retro || line.line_type === 'retro') return 'bg-amber-50 border-l-4 border-amber-300';
    if (line.amount < 0) return 'bg-red-50 border-l-4 border-red-300';
    return 'bg-green-50 border-l-4 border-green-300';
  };

  const calculateRetroTotal = (lines) => {
    return lines
      .filter(line => line.is_retro || line.line_type === 'retro')
      .reduce((sum, line) => sum + line.amount, 0);
  };

  const getCategoryFor = (topicCode) => {
    return ministryCodeCategory.get(String(topicCode)) || 'כללי';
  };

  // Phase 3.1: Hebrew labels for raw ingestion line_type buckets.
  const LINE_TYPE_LABELS = {
    gy: 'גנים יומיים (GY)',
    sharatim: 'שרתים',
    mutavim: 'מותאמים',
    yadaniim: 'ידניים',
    moadon: 'מועדון',
    sacal: 'סקאל',
    mucarim: 'מוכרים',
    hasaot: 'הסעות',
    shefi: 'שפ״י',
    cheshbonit: 'חשבונית (לא כוסה)',
    retro: 'רטרו',
    shortage: 'חוסר',
    adjustment: 'התאמה',
    regular: 'רגיל',
  };
  const formatLineTypeLabel = (lt) => LINE_TYPE_LABELS[lt] || (lt ? lt : 'רגיל');

  const buildCategoriesInOrder = (codes) => {
    const categoryMap = {};

    // Group codes by category
    codes.forEach(code => {
      const category = getCategoryFor(code);
      if (!categoryMap[category]) {
        categoryMap[category] = { codes: [], total: 0 };
      }
      categoryMap[category].codes.push(code);
      const codeTotal = (groupedLines[code] || []).reduce((sum, line) => sum + line.amount, 0);
      categoryMap[category].total += codeTotal;
    });

    // Sort categories: by total descending, then by Hebrew alphabetical order
    const categories = Object.keys(categoryMap).sort((a, b) => {
      const totalDiff = categoryMap[b].total - categoryMap[a].total;
      if (totalDiff !== 0) return totalDiff;
      return a.localeCompare(b, 'he');
    });

    return categories.map(category => ({
      category,
      codes: categoryMap[category].codes,
      total: categoryMap[category].total
    }));
  };

  // PREPARE DATA FOR RENDERING

  const activeLines = filterActiveLines(budget?.budget_lines || []);
  const groupedLines = groupByTopicCode(activeLines);
  const sortedCodes = Object.keys(groupedLines).filter(code => code !== '0').sort();
  const displayedLines = sortedCodes.flatMap((code) => groupedLines[code] || []);
  const displayedRowsTotal = displayedLines.reduce((sum, line) => sum + Number(line.amount || 0), 0);
  const retroTotal = calculateRetroTotal(budget?.budget_lines || []);
  const retroSchoolYearGroups = buildRetroSchoolYearGroups(budget?.budget_lines || []);

  useEffect(() => {
    if (retroSchoolYearGroups.length === 0) {
      setExpandedRetroSchoolYears({});
      return;
    }

    const [latest] = retroSchoolYearGroups;
    const nextState = { [latest.key]: true };
    retroSchoolYearGroups.slice(1).forEach((group) => {
      nextState[group.key] = false;
    });
    setExpandedRetroSchoolYears(nextState);
  }, [selectedMonth, retroSchoolYearGroups.length]);

  const rawBreakdownTotal = Number(budget?.breakdown_total || 0);
  const rawInvoiceTotal = Number(budget?.invoice_total || 0);
  // Normalize mapping so "Due" follows the rows shown in this table.
  const dueIsBreakdown = Math.abs(displayedRowsTotal - rawBreakdownTotal) <= Math.abs(displayedRowsTotal - rawInvoiceTotal);
  const dueTotal = dueIsBreakdown ? rawBreakdownTotal : rawInvoiceTotal;
  const paidTotal = dueIsBreakdown ? rawInvoiceTotal : rawBreakdownTotal;
  const gapTotal = dueTotal - paidTotal;
  const categoriesInOrder = buildCategoriesInOrder(sortedCodes);

  const pageAmounts = useMemo(() => {
    const lineAmounts = (budget?.budget_lines || []).map((line) => Number(line.amount || 0));
    const changeAmounts = Object.values(budget?.month_changes?.changes_by_topic || {}).flatMap((change) => [
      Number(change?.prev_total || 0),
      Number(change?.curr_total || 0),
      Number(change?.amount_change || 0),
    ]);
    return [
      ...lineAmounts,
      ...changeAmounts,
      dueTotal,
      paidTotal,
      gapTotal,
      retroTotal,
      displayedRowsTotal,
    ];
  }, [budget?.budget_lines, budget?.month_changes?.changes_by_topic, dueTotal, paidTotal, gapTotal, retroTotal, displayedRowsTotal]);

  const concreteRoundingMode = resolveConcreteMode(roundingMode, pageAmounts);
  const disclosureText = getRoundingDisclosureText(concreteRoundingMode);
  const formatShekelText = (amount) => formatShekelByMode(amount, { mode: concreteRoundingMode });

  const parseDisplayedAmount = (amount) => {
    const formatted = formatShekelText(amount);
    const normalized = formatted.replace(/[^0-9,.-]/g, '').replace(/,/g, '');
    const parsed = Number(normalized);
    return Number.isFinite(parsed) ? parsed : 0;
  };

  const displayedSubtotalSum = categoriesInOrder.reduce((sum, categoryItem) => sum + parseDisplayedAmount(categoryItem.total), 0);
  const displayedGrandTotal = parseDisplayedAmount(displayedRowsTotal);
  const hasRoundingResidual =
    concreteRoundingMode !== ROUNDING_MODES.EXACT &&
    Math.abs(displayedSubtotalSum - displayedGrandTotal) > 0.000001;

  const status = getBudgetStatus({
    dueAmount: dueTotal,
    paidAmount: paidTotal,
    month: selectedMonth,
  });
  const statusBadge = getBudgetStatusBadge(status.key);
  const monthChangesThreshold = Math.min(Math.abs(gapTotal) * 0.05, 10000);
  const significantMonthChanges = Object.entries(budget?.month_changes?.changes_by_topic || {})
    .filter(([code, change]) => {
      if (code === '0') return false;
      return Math.abs(Number(change?.amount_change || 0)) >= monthChangesThreshold;
    });

  if (!selectedMonth) {
    return (
      <PageWrapper title="פירוט תקציב">
        <div className="text-center text-neutral-600 font-hebrew">בחירת חודש...</div>
      </PageWrapper>
    );
  }

  return (
    <PageWrapper 
      title={`${budget?.municipality.name || 'עיר'} — ${formatHebrewDate(selectedMonth)}`}
    >
      <div className="w-full max-w-6xl mx-auto px-4">
        {/* Back Button */}
        <div className="mb-6">
          <button
            onClick={handleBack}
            className="flex items-center gap-2 text-primary-600 hover:text-primary-700 font-hebrew font-semibold transition"
          >
            <ArrowRight size={20} />
            חזור לסיכום
          </button>
        </div>

        {/* Month Selector */}
        <div className="mb-6">
          <select
            value={selectedMonth}
            onChange={(e) => setSelectedMonth(e.target.value)}
            className="w-full md:w-40 border border-neutral-300 rounded-lg px-3 py-2 text-sm font-hebrew bg-white"
          >
            {months.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-16">
            <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        )}

        {error && (
          <div className="p-6 bg-red-50 border border-red-200 rounded-xl text-center text-red-800 font-hebrew mb-6 shadow-md">
            {error}
          </div>
        )}

        {budget && (
          <>
            {/* PAGE HEADER - STATUS BADGE */}
            <div className="mb-8 flex items-center justify-between flex-wrap gap-3">
              <h1 className="text-4xl font-bold text-slate-900 font-hebrew flex-1">פירוט תקציב מפורט</h1>
              <div className="flex items-center gap-3">
                <RoundingModeToggle mode={roundingMode} onChange={setRoundingMode} />
                <ReviewStatusControl
                  status={budget.review_status || 'pending'}
                  note={budget.review_status_note || ''}
                  reviewerName={budget.reviewed_by_name || ''}
                  reviewedAt={budget.reviewed_at || ''}
                  editable
                  onPersist={handlePersistReviewStatus}
                />
                {/* PDF Download button */}
                <button
                  onClick={handleGeneratePdf}
                  disabled={pdfGenerating}
                  className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-xl font-hebrew font-bold text-sm transition-colors shadow"
                  dir="rtl"
                >
                  {pdfGenerating ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      מייצר PDF...
                    </>
                  ) : '📥 הורד דוח'}
                </button>
                <span className={`px-6 py-3 rounded-full border font-hebrew font-semibold text-base ${statusBadge.className} shadow-md`}>
                  {statusBadge.icon} {statusBadge.text}
                </span>
              </div>
            </div>

            <div className="mb-6">
              <RoundingDisclosureBanner text={disclosureText} />
            </div>

            {/* CPA Insights Panel — computed review blocks */}
            <div className="mb-8">
              <CpaInsightsPanel
                municipalityId={Number(id)}
                month={selectedMonth}
                roundingMode={concreteRoundingMode}
              />
            </div>

            {/* PDF toast */}
            {pdfToast && (
              <div className={`mb-4 px-4 py-3 rounded-xl font-hebrew text-sm font-medium ${
                pdfToast.type === 'error' ? 'bg-red-50 text-red-700 border border-red-200' :
                pdfToast.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' :
                'bg-blue-50 text-blue-700 border border-blue-200'
              }`} dir="rtl">
                {pdfToast.msg}
              </div>
            )}

            {/* SUMMARY CARDS ROW */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
              {/* Card 1: סכום מגיע */}
              <div className="bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition border border-blue-100">
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-4xl">💰</span>
                  <p className="text-base font-hebrew text-blue-700 font-semibold">סכום מגיע</p>
                </div>
                <p className="text-3xl font-bold text-blue-900 font-hebrew">
                  <ShekelAmount amount={dueTotal} mode={concreteRoundingMode} />
                </p>
              </div>

              {/* Card 2: סכום שולם */}
              <div className="bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition border border-green-100">
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-4xl">✅</span>
                  <p className="text-base font-hebrew text-green-700 font-semibold">סכום שולם</p>
                </div>
                <p className="text-3xl font-bold text-green-900 font-hebrew">
                  <ShekelAmount amount={paidTotal} mode={concreteRoundingMode} />
                </p>
              </div>

              {/* Card 3: הפרש */}
              <div className={`bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition border ${gapTotal < 0 ? 'border-red-100' : 'border-green-100'}`}>
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-4xl">↕ן¸</span>
                  <p className={`text-base font-hebrew font-semibold ${gapTotal < 0 ? 'text-red-700' : 'text-green-700'}`}>
                    הפרש
                  </p>
                </div>
                <p className={`text-3xl font-bold font-hebrew ${gapTotal < 0 ? 'text-red-900' : 'text-green-900'}`}>
                  <ShekelAmount amount={gapTotal} mode={concreteRoundingMode} />
                </p>
              </div>

              {/* Card 4: סה"כ רטרו */}
              <div className="bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition border border-amber-100">
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-4xl">📅</span>
                  <p className="text-base font-hebrew text-amber-700 font-semibold">סה"כ רטרו</p>
                </div>
                <p className="text-3xl font-bold text-amber-900 font-hebrew">
                  <ShekelAmount amount={retroTotal} mode={concreteRoundingMode} />
                </p>
              </div>
            </div>

            {retroSchoolYearGroups.length > 0 && (
              <div className="bg-white rounded-2xl shadow-lg border border-amber-200 overflow-hidden mb-10">
                <div className="px-8 py-5 border-b border-amber-200 bg-amber-50">
                  <h2 className="font-hebrew font-bold text-2xl text-amber-900">רטרו לפי שנת לימודים</h2>
                </div>

                <div className="divide-y divide-amber-100">
                  {retroSchoolYearGroups.map((schoolYear) => {
                    const isExpanded = expandedRetroSchoolYears[schoolYear.key] === true;

                    return (
                      <div key={schoolYear.key} className="bg-white">
                        <button
                          type="button"
                          onClick={() => toggleSchoolYearExpanded(schoolYear.key)}
                          className="w-full px-8 py-5 hover:bg-amber-50/40 transition text-right"
                        >
                          <div className="flex items-center justify-between gap-4">
                            <div className="text-right">
                              <p className="font-hebrew font-bold text-xl text-slate-900">{schoolYear.label}</p>
                              <p className="font-hebrew text-sm text-slate-600">{schoolYear.subtitle}</p>
                              <p className="font-hebrew text-xs text-slate-500 mt-1">
                                {schoolYear.retroLineCount} שורות רטרו
                              </p>
                            </div>
                            <div className="flex items-center gap-5">
                              <p className="font-bold text-lg text-amber-900">{schoolYear.retroTotalFormatted}</p>
                              <span className="text-lg font-hebrew text-slate-700">{isExpanded ? '▼' : '▶'}</span>
                            </div>
                          </div>
                        </button>

                        {isExpanded && (
                          <div className="px-8 pb-6 space-y-3">
                            {schoolYear.codes.map((codeGroup) => {
                              const summary = budget.summary_by_topic?.[codeGroup.code] || {};
                              const topicName = summary.topic_name || codeGroup.lines[0]?.budget_topic || `קוד ${codeGroup.code}`;

                              return (
                                <div key={`${schoolYear.key}-${codeGroup.code}`} className="border border-slate-200 rounded-xl overflow-hidden">
                                  <div className="px-5 py-4 bg-amber-50 border-b border-amber-100 flex items-center justify-between">
                                    <p className="font-hebrew font-semibold text-slate-900">
                                      🟡 {topicName} — קוד {codeGroup.code}
                                    </p>
                                    <p className="font-bold text-slate-900"><ShekelAmount amount={codeGroup.total} mode={concreteRoundingMode} /></p>
                                  </div>

                                  <div className="divide-y divide-slate-100">
                                    {codeGroup.lines.map((line) => (
                                      <div key={line.id} className={`p-4 ${getLineColor(line)}`}>
                                        <div className="flex items-center justify-between gap-4">
                                          <div className="text-right">
                                            <p className="font-hebrew font-medium text-slate-900">{line.budget_topic}</p>
                                            <p className="font-hebrew text-sm text-slate-600 mt-1">
                                              חודש תחולה: {formatEffectiveMonth(line.period_month)}
                                            </p>
                                          </div>
                                          <p className="font-bold text-slate-900 text-lg"><ShekelAmount amount={line.amount} mode={concreteRoundingMode} /></p>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* WHAT CHANGED THIS MONTH */}
            {budget.month_changes?.has_changes && significantMonthChanges.length > 0 && (
              <div className="bg-white rounded-2xl p-8 mb-10 shadow-lg border border-blue-200">
                <div className="flex items-center justify-between gap-4 mb-6" dir="rtl">
                  <h2 className="font-hebrew font-bold text-2xl text-blue-900">
                    🔄 מה השתנה החודש? (בהשוואה ל-{budget.month_changes.previous_month})
                  </h2>
                  {Object.keys(studentCountDeltas).length > 0 && (
                    <label className="flex items-center gap-2 text-sm font-hebrew text-slate-700 select-none">
                      <input
                        type="checkbox"
                        checked={onlyStudentCountChanges}
                        onChange={(e) => setOnlyStudentCountChanges(e.target.checked)}
                        className="h-4 w-4 accent-blue-600"
                      />
                      הצג רק שינויים שנגרמו ממספר ילדים
                    </label>
                  )}
                </div>
                <div className="space-y-4">
                  {significantMonthChanges
                    .filter(([code]) => {
                      if (!onlyStudentCountChanges) return true;
                      const d = studentCountDeltas[String(code)];
                      return d && d.variance_driver === 'student_count';
                    })
                    .map(([code, change]) => (
                    <div key={code} className="bg-gradient-to-r from-blue-50 to-white border border-blue-100 rounded-xl p-5">
                      <div className="flex flex-wrap items-center justify-between gap-2 mb-3" dir="rtl">
                        <p className="font-hebrew font-semibold text-lg text-slate-900">
                          {change.topic_name} — קוד {code}
                        </p>
                        <StudentCountDeltaChip delta={studentCountDeltas[String(code)]} showDriverBadge />
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-base font-hebrew">
                        {/* Items count change */}
                        <div className={`flex items-baseline gap-2 ${change.items_change !== 0 ? 'text-neutral-700' : 'text-neutral-500'}`}>
                          <span className="font-semibold">פריטים:</span>
                          <span className="text-neutral-600">
                            {change.prev_lines_count} ← {change.curr_lines_count}
                          </span>
                          {change.items_change !== 0 && (
                            <span className={change.items_change > 0 ? 'text-green-700 font-bold' : 'text-red-700 font-bold'}>
                              {change.items_change > 0 ? '+' : ''}{change.items_change}
                            </span>
                          )}
                        </div>
                        
                        {/* Amount change */}
                        <div className={`flex items-baseline gap-2 ${change.amount_change !== 0 ? 'text-neutral-700' : 'text-neutral-500'}`}>
                          <span className="font-semibold">סכום:</span>
                          <span className="text-neutral-600">
                            {formatShekelText(change.prev_total)} ← {formatShekelText(change.curr_total)}
                          </span>
                          {change.amount_change !== 0 && (
                            <span className={change.amount_change > 0 ? 'text-green-700 font-bold' : 'text-red-700 font-bold'}>
                              ({change.amount_change > 0 ? '+' : ''}{formatShekelText(change.amount_change)} • {change.amount_change_pct > 0 ? '+' : ''}{change.amount_change_pct}%)
                            </span>
                          )}
                        </div>
                      </div>
                      {(() => {
                        const dropItems = Number(change.items_change || 0);
                        const prevMonthAmount = Number(change.prev_total || 0);
                        const droppedToZero = Number(change.curr_lines_count || 0) === 0;
                        const shouldAppendDropInterpretation =
                          dropItems < 0 && droppedToZero && prevMonthAmount > 5000;

                        let explanation = generateChangeExplanation(change, explanations[change.topic_code]);

                        if (dropItems < 0) {
                          const amountChange = Number(change.amount_change || 0);
                          const amountChangePct = Number(change.amount_change_pct || 0);
                          const numericDropText = `${Math.abs(dropItems)} פריטים הוסרו (${amountChange > 0 ? '+' : ''}${formatShekelText(amountChange)} • ${amountChangePct > 0 ? '+' : ''}${amountChangePct}%)`;
                          explanation = {
                            text: shouldAppendDropInterpretation
                              ? `${numericDropText} — ייתכן סגירת משרות או סיום תשלומים`
                              : numericDropText,
                            isCustom: false,
                          };
                        }

                        return <ChangeExplanationBox explanation={explanation.text} isCustom={explanation.isCustom} />;
                      })()}
                    </div>
                  ))}
                </div>
              </div>
            )}
            {/* BUDGET TABLE - GROUPED BY CATEGORY THEN BY BUDGET CODE */}
            <div className="bg-white rounded-2xl shadow-lg border border-slate-200 overflow-hidden mb-10">
              <div className="space-y-0">
                {sortedCodes.length > 0 ? (
                  categoriesInOrder.map((categoryItem) => {
                    const { category, codes: codeList, total: categoryTotal } = categoryItem;
                    const isHighSchoolCategory = category === 'חטיבה עליונה';
                    const isCategoryExpanded = expandedCategories[category] !== false; // Default to expanded

                    return (
                      <div key={category} className="border-b border-slate-200 last:border-b-0">
                        {/* CATEGORY HEADER */}
                        <div
                          className="flex items-center justify-between px-8 py-4 bg-slate-50 hover:bg-slate-100 cursor-pointer border-b-2 border-slate-300 transition"
                          onClick={() => toggleCategoryExpanded(category)}
                        >
                          <div className="flex items-center gap-4 flex-1">
                            <span className="text-lg font-hebrew">
                              {isCategoryExpanded ? '▼' : '▶'}
                            </span>
                            <div className="flex-1">
                              <h2 className="font-hebrew font-bold text-lg text-slate-900">{category}</h2>
                              <p className="font-hebrew text-sm text-slate-600 mt-1">
                                {codeList.length} נושא{codeList.length === 1 ? '' : 'ים'}
                              </p>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className="font-bold text-lg text-slate-900">
                              <ShekelAmount amount={categoryTotal} mode={concreteRoundingMode} />
                            </p>
                          </div>
                        </div>

                        {/* CODES WITHIN CATEGORY */}
                        {isCategoryExpanded && (
                          <div className="space-y-0">
                            {codeList.map((topicCode) => {
                              const groupLines = groupedLines[topicCode];
                              const groupTotal = groupLines.reduce((sum, line) => sum + line.amount, 0);
                              const summary = budget.summary_by_topic?.[topicCode] || {};
                              const topicName = summary.topic_name || groupLines[0]?.budget_topic || `קוד ${topicCode}`;
                              const colors = getGroupColor(groupLines);
                              const isExpanded = expandedGroups[topicCode] || false;

                              return (
                                <div key={topicCode} className={`border-b border-slate-200 last:border-b-0 ${colors.bg}`}>
                                  <div
                                    className={`px-8 py-5 cursor-pointer hover:bg-opacity-80 transition ${colors.border} flex items-center justify-between rounded-xl`}
                                    onClick={() => toggleGroupExpanded(topicCode)}
                                  >
                                    <div className="flex items-center gap-4 flex-1">
                                      <span className="text-lg">{isExpanded ? '▼' : '▶'}</span>
                                      <div className="flex-1">
                                        <h3 className="font-hebrew font-bold text-base text-neutral-900">
                                          {colors.badge} {topicName} — קוד {topicCode}
                                        </h3>
                                        <p className="font-hebrew text-xs text-neutral-600 mt-1">
                                          {groupLines.length} {groupLines.length === 1 ? 'פריט' : 'פריטים'}
                                        </p>
                                      </div>
                                    </div>
                                    <div className="text-right">
                                      <p className="font-bold text-lg text-neutral-900">
                                        <ShekelAmount amount={groupTotal} mode={concreteRoundingMode} />
                                      </p>
                                      {studentCountDeltas[String(topicCode)] && (
                                        <StudentCountDeltaChip delta={studentCountDeltas[String(topicCode)]} showDriverBadge />
                                      )}
                                    </div>
                                  </div>

                                  {isExpanded && (
                                    <div className="px-8 py-6 space-y-4 border-t border-slate-200 bg-opacity-50">
                                      {summary.topic_name && (
                                        <div className="mb-5 p-4 bg-blue-50 border border-blue-200 rounded-xl text-base font-hebrew text-blue-900">
                                          {explanations[topicCode] || `${summary.topic_name}: ${groupLines.length} פריט${groupLines.length > 1 ? 'ים' : ''} בסך הכל ${formatShekelText(groupTotal)}`}
                                        </div>
                                      )}

                                      <div className="space-y-3">
                                        {groupLines.map((line) => {
                                          const lineColor = getLineColor(line);
                                          const smartExp = smartExplanations[topicCode];

                                          return (
                                            <div key={line.id} className={`p-4 rounded-lg border-l-4 ${lineColor}`}>
                                              <div className="flex items-center justify-between mb-2">
                                                <p className="font-hebrew font-medium text-slate-900 flex-1">{line.budget_topic}</p>
                                                <div className="flex items-center gap-3">
                                                  <p className="font-bold text-slate-900 ml-4 text-lg">
                                                    <ShekelAmount amount={line.amount} mode={concreteRoundingMode} />
                                                  </p>
                                                  <button
                                                    onClick={() => {
                                                      setEditingTopicCode(topicCode);
                                                      setEditingTopicName(summary.topic_name || groupLines[0]?.budget_topic || `קוד ${topicCode}`);
                                                    }}
                                                    title="ערוך הסבר"
                                                    className="p-2 bg-blue-100 hover:bg-blue-200 text-blue-600 rounded-lg transition text-lg"
                                                  >
                                                    ✏️
                                                  </button>
                                                </div>
                                              </div>
                                              <p className="text-sm font-hebrew text-slate-600 mb-3">
                                                חודש: {line.period_month}
                                                {(line.is_retro || line.line_type === 'retro') && ' • רטרו'}
                                                {line.amount < 0 && ' • ירידה'}
                                              </p>

                                              {smartExp && (
                                                <div className="mt-3 pt-3 border-t border-opacity-30">
                                                  <SmartExplanationDisplay smartExplanation={smartExp} topicCode={topicCode} />
                                                </div>
                                              )}
                                            </div>
                                          );
                                        })}
                                      </div>
                                      {/* Phase 3.1: Per-line institutional drill-down. */}
                                      {(() => {
                                        const detail = topicLinesDetail[topicCode];
                                        const isDetailOpen = detail?.expanded;
                                        return (
                                          <div className="mt-4 border-t border-slate-200 pt-4">
                                            <button
                                              type="button"
                                              onClick={() => toggleTopicLinesDetail(topicCode)}
                                              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-hebrew bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition"
                                            >
                                              <span>{isDetailOpen ? '▼' : '▶'}</span>
                                              <span>פירוט שורות לפי מוסד / תת־נושא</span>
                                              {detail?.loading && (
                                                <span className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                                              )}
                                            </button>

                                            {/* Priority-3: 12-month sparkline for this topic */}
                                            {isDetailOpen && (
                                              <div className="mt-4 p-3 bg-slate-50 rounded-lg border border-slate-200">
                                                <div className="text-xs font-hebrew text-slate-500 mb-2 text-right">
                                                  מגמת 12 חודשים אחרונים — קוד {topicCode}
                                                </div>
                                                <Sparkline
                                                  municipalityId={Number(id)}
                                                  topicCode={topicCode}
                                                  height={80}
                                                  showAxis
                                                />
                                              </div>
                                            )}

                                            {isDetailOpen && detail?.error && (
                                              <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm font-hebrew text-red-700">
                                                {detail.error}
                                              </div>
                                            )}

                                            {isDetailOpen && detail?.data && (
                                              <div className="mt-4 space-y-4">
                                                <div className="flex flex-wrap gap-2">
                                                  {Object.entries(detail.data.by_line_type || {}).map(([lt, summary]) => (
                                                    <span
                                                      key={lt}
                                                      className="inline-flex items-center gap-2 px-3 py-1 bg-slate-100 border border-slate-200 rounded-full text-xs font-hebrew text-slate-700"
                                                    >
                                                      <span className="font-semibold">{formatLineTypeLabel(lt)}</span>
                                                      <span className="text-slate-500">•</span>
                                                      <span>{summary.count} שורות</span>
                                                      <span className="text-slate-500">•</span>
                                                      <span className="font-bold text-slate-900">
                                                        {formatShekelText(summary.total)}
                                                      </span>
                                                    </span>
                                                  ))}
                                                  <span className="inline-flex items-center gap-2 px-3 py-1 bg-blue-100 border border-blue-200 rounded-full text-xs font-hebrew text-blue-800">
                                                    <span className="font-semibold">סה״כ {detail.data.row_count} שורות</span>
                                                    <span>{formatShekelText(detail.data.total)}</span>
                                                  </span>
                                                </div>

                                                <div className="overflow-x-auto border border-slate-200 rounded-lg bg-white">
                                                  <table className="w-full text-sm text-right">
                                                    <thead className="bg-slate-50 border-b border-slate-200">
                                                      <tr className="font-hebrew text-xs text-slate-600">
                                                        <th className="px-3 py-2 font-bold">סוג</th>
                                                        <th className="px-3 py-2 font-bold">סכום</th>
                                                        <th className="px-3 py-2 font-bold">חודש</th>
                                                        <th className="px-3 py-2 font-bold">ילדים</th>
                                                        <th className="px-3 py-2 font-bold">השתתפות</th>
                                                        <th className="px-3 py-2 font-bold">מניע שונות</th>
                                                        <th className="px-3 py-2 font-bold">הערות</th>
                                                      </tr>
                                                    </thead>
                                                    <tbody>
                                                      {detail.data.rows.map((row) => (
                                                        <tr
                                                          key={row.id}
                                                          className={`border-b border-slate-100 last:border-b-0 ${row.is_retro ? 'bg-amber-50/40' : row.amount < 0 ? 'bg-red-50/40' : ''}`}
                                                        >
                                                          <td className="px-3 py-2">
                                                            <span className="inline-block px-2 py-0.5 bg-slate-200 text-slate-800 rounded text-xs font-hebrew font-medium">
                                                              {formatLineTypeLabel(row.line_type)}
                                                            </span>
                                                          </td>
                                                          <td className="px-3 py-2 font-bold text-slate-900 whitespace-nowrap">
                                                            <ShekelAmount amount={row.amount} mode={concreteRoundingMode} />
                                                          </td>
                                                          <td className="px-3 py-2 text-slate-600 font-hebrew whitespace-nowrap">
                                                            {row.period_month}
                                                            {row.is_retro && <span className="mr-1 text-amber-700">• רטרו</span>}
                                                          </td>
                                                          <td className="px-3 py-2 text-slate-700">
                                                            {row.num_children != null ? row.num_children : '—'}
                                                          </td>
                                                          <td className="px-3 py-2 text-slate-700">
                                                            {row.participation_pct != null
                                                              ? `${Number(row.participation_pct).toFixed(1)}%`
                                                              : '—'}
                                                          </td>
                                                          <td className="px-3 py-2 text-slate-700 font-hebrew">
                                                            {row.variance_driver || '—'}
                                                          </td>
                                                          <td className="px-3 py-2 text-slate-600 font-hebrew text-xs max-w-xs truncate" title={row.notes || ''}>
                                                            {row.notes || '—'}
                                                          </td>
                                                        </tr>
                                                      ))}
                                                    </tbody>
                                                  </table>
                                                </div>
                                              </div>
                                            )}
                                          </div>
                                        );
                                      })()}

                                      {/* Phase 3.2: Formula-variance drill-down — enrollment Δ, positions Δ, rate Δ. */}
                                      {(() => {
                                        const driversState = formulaDrivers[topicCode];
                                        const isDriversOpen = driversState?.expanded;
                                        const d = driversState?.data;
                                        return (
                                          <div className="mt-4 border-t border-slate-200 pt-4">
                                            <button
                                              type="button"
                                              onClick={() => toggleFormulaDrivers(topicCode)}
                                              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-hebrew bg-white border border-indigo-300 rounded-lg hover:bg-indigo-50 transition"
                                            >
                                              <span>{isDriversOpen ? '▼' : '▶'}</span>
                                              <span>מניעי שונות — ילדים, משרות, תעריף</span>
                                              {driversState?.loading && (
                                                <span className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                                              )}
                                            </button>

                                            {isDriversOpen && driversState?.error && (
                                              <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm font-hebrew text-red-700">
                                                {driversState.error}
                                              </div>
                                            )}

                                            {isDriversOpen && d && (
                                              <div className="mt-4 space-y-4">
                                                <div className="p-4 bg-gradient-to-l from-indigo-50 to-white border border-indigo-200 rounded-lg">
                                                  <div className="flex flex-wrap items-baseline gap-4 font-hebrew text-sm">
                                                    <div>
                                                      <span className="text-slate-600">
                                                        {d.previous_month || '—'} → {d.month}:
                                                      </span>
                                                      <span className={`mr-2 font-bold ${d.amount.delta_total < 0 ? 'text-red-700' : 'text-emerald-700'}`}>
                                                        {d.amount.delta_total >= 0 ? '+' : ''}
                                                        {formatShekelText(d.amount.delta_total)}
                                                      </span>
                                                      {d.amount.delta_pct != null && (
                                                        <span className={`mr-1 text-xs ${d.amount.delta_pct < 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                                                          ({d.amount.delta_pct > 0 ? '+' : ''}{d.amount.delta_pct}%)
                                                        </span>
                                                      )}
                                                    </div>
                                                    <div className="text-slate-600">
                                                      מהם רגיל:{' '}
                                                      <span className={`font-bold ${d.amount.delta_regular < 0 ? 'text-red-700' : 'text-emerald-700'}`}>
                                                        {d.amount.delta_regular >= 0 ? '+' : ''}
                                                        {formatShekelText(d.amount.delta_regular)}
                                                      </span>
                                                    </div>
                                                  </div>
                                                </div>

                                                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                                  <div className="p-3 border border-slate-200 rounded-lg bg-white">
                                                    <div className="text-xs font-hebrew text-slate-500 mb-1">שינוי בתלמידים (ICHLUSKITOT)</div>
                                                    <div className="flex items-baseline gap-2 font-hebrew">
                                                      <span className={`text-2xl font-bold ${d.enrollment_delta.delta_total < 0 ? 'text-red-700' : d.enrollment_delta.delta_total > 0 ? 'text-emerald-700' : 'text-slate-500'}`}>
                                                        {d.enrollment_delta.delta_total >= 0 ? '+' : ''}
                                                        {d.enrollment_delta.delta_total}
                                                      </span>
                                                      <span className="text-xs text-slate-500">
                                                        ({d.enrollment_delta.prev_total} → {d.enrollment_delta.curr_total})
                                                      </span>
                                                    </div>
                                                  </div>

                                                  <div className="p-3 border border-slate-200 rounded-lg bg-white">
                                                    <div className="text-xs font-hebrew text-slate-500 mb-1">שינוי ב־FTE (משרות רלוונטיות)</div>
                                                    <div className="flex items-baseline gap-2 font-hebrew">
                                                      <span className={`text-2xl font-bold ${d.positions_delta.delta_total_fte < 0 ? 'text-red-700' : d.positions_delta.delta_total_fte > 0 ? 'text-emerald-700' : 'text-slate-500'}`}>
                                                        {d.positions_delta.delta_total_fte >= 0 ? '+' : ''}
                                                        {d.positions_delta.delta_total_fte}
                                                      </span>
                                                      <span className="text-xs text-slate-500">
                                                        ({d.positions_delta.prev_total_fte} → {d.positions_delta.curr_total_fte})
                                                      </span>
                                                    </div>
                                                  </div>

                                                  <div className="p-3 border border-slate-200 rounded-lg bg-white">
                                                    <div className="text-xs font-hebrew text-slate-500 mb-1">
                                                      שינוי בתעריף לילד
                                                      {d.rate_delta.kids_source === 'enrollment_total' && (
                                                        <span className="mr-1 text-slate-400">(לפי ICHLUSKITOT)</span>
                                                      )}
                                                    </div>
                                                    <div className="flex items-baseline gap-2 font-hebrew">
                                                      {d.rate_delta.delta_rate_per_child != null ? (
                                                        <>
                                                          <span className={`text-2xl font-bold ${d.rate_delta.delta_rate_per_child < 0 ? 'text-red-700' : d.rate_delta.delta_rate_per_child > 0 ? 'text-emerald-700' : 'text-slate-500'}`}>
                                                            {d.rate_delta.delta_rate_per_child >= 0 ? '+' : ''}
                                                            {formatShekelText(d.rate_delta.delta_rate_per_child)}
                                                          </span>
                                                          <span className="text-xs text-slate-500">
                                                            ({formatShekelText(d.rate_delta.prev_rate_per_child)} → {formatShekelText(d.rate_delta.curr_rate_per_child)})
                                                          </span>
                                                        </>
                                                      ) : (
                                                        <span className="text-sm text-slate-400">—</span>
                                                      )}
                                                    </div>
                                                  </div>
                                                </div>

                                                {d.explained && (
                                                  <div className="p-4 border border-amber-200 bg-amber-50/50 rounded-lg font-hebrew text-sm">
                                                    <div className="font-bold text-slate-800 mb-2">פירוק השונות (דלתא רגיל)</div>
                                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                                                      <div>
                                                        <div className="text-slate-500">מדלתא כוללת</div>
                                                        <div className={`font-bold text-base ${d.explained.delta_regular < 0 ? 'text-red-700' : 'text-emerald-700'}`}>
                                                          {formatShekelText(d.explained.delta_regular)}
                                                        </div>
                                                      </div>
                                                      <div>
                                                        <div className="text-slate-500">מיוחס לשינוי בתלמידים</div>
                                                        <div className={`font-bold text-base ${d.explained.from_enrollment < 0 ? 'text-red-700' : 'text-emerald-700'}`}>
                                                          {formatShekelText(d.explained.from_enrollment)}
                                                        </div>
                                                      </div>
                                                      <div>
                                                        <div className="text-slate-500">מיוחס לשינוי בתעריף</div>
                                                        <div className={`font-bold text-base ${d.explained.from_rate < 0 ? 'text-red-700' : 'text-emerald-700'}`}>
                                                          {formatShekelText(d.explained.from_rate)}
                                                        </div>
                                                      </div>
                                                      <div>
                                                        <div className="text-slate-500">שארית לא מוסברת</div>
                                                        <div className={`font-bold text-base ${Math.abs(d.explained.residual) > 100 ? 'text-amber-700' : 'text-slate-500'}`}>
                                                          {formatShekelText(d.explained.residual)}
                                                        </div>
                                                      </div>
                                                    </div>
                                                  </div>
                                                )}

                                                {d.positions_delta.by_role.filter((p) => p.relevant_to_topic).length > 0 && (
                                                  <div className="overflow-x-auto border border-slate-200 rounded-lg bg-white">
                                                    <div className="px-3 py-2 bg-slate-50 border-b border-slate-200 font-hebrew text-xs text-slate-700 font-bold">
                                                      משרות רלוונטיות לנושא
                                                    </div>
                                                    <table className="w-full text-sm text-right">
                                                      <thead className="bg-slate-50 border-b border-slate-200">
                                                        <tr className="font-hebrew text-xs text-slate-600">
                                                          <th className="px-3 py-2 font-bold">תפקיד</th>
                                                          <th className="px-3 py-2 font-bold">FTE קודם</th>
                                                          <th className="px-3 py-2 font-bold">FTE נוכחי</th>
                                                          <th className="px-3 py-2 font-bold">Δ FTE</th>
                                                        </tr>
                                                      </thead>
                                                      <tbody>
                                                        {d.positions_delta.by_role
                                                          .filter((p) => p.relevant_to_topic)
                                                          .map((row) => (
                                                            <tr key={`${row.scope}-${row.role}`} className="border-b border-slate-100 last:border-b-0">
                                                              <td className="px-3 py-2 font-hebrew text-slate-800">{row.role}</td>
                                                              <td className="px-3 py-2 text-slate-700 font-hebrew">{row.prev_fte}</td>
                                                              <td className="px-3 py-2 text-slate-700 font-hebrew">{row.curr_fte}</td>
                                                              <td className={`px-3 py-2 font-bold font-hebrew ${row.delta_fte < 0 ? 'text-red-700' : row.delta_fte > 0 ? 'text-emerald-700' : 'text-slate-500'}`}>
                                                                {row.delta_fte >= 0 ? '+' : ''}{row.delta_fte}
                                                              </td>
                                                            </tr>
                                                          ))}
                                                      </tbody>
                                                    </table>
                                                  </div>
                                                )}

                                                {d.enrollment_delta.by_institution.length > 0 && (
                                                  <div className="overflow-x-auto border border-slate-200 rounded-lg bg-white">
                                                    <div className="px-3 py-2 bg-slate-50 border-b border-slate-200 font-hebrew text-xs text-slate-700 font-bold">
                                                      שינוי מצבת תלמידים לפי מוסד (10 מובילים)
                                                    </div>
                                                    <table className="w-full text-sm text-right">
                                                      <thead className="bg-slate-50 border-b border-slate-200">
                                                        <tr className="font-hebrew text-xs text-slate-600">
                                                          <th className="px-3 py-2 font-bold">מוסד</th>
                                                          <th className="px-3 py-2 font-bold">קוד</th>
                                                          <th className="px-3 py-2 font-bold">קודם</th>
                                                          <th className="px-3 py-2 font-bold">נוכחי</th>
                                                          <th className="px-3 py-2 font-bold">Δ</th>
                                                        </tr>
                                                      </thead>
                                                      <tbody>
                                                        {d.enrollment_delta.by_institution.slice(0, 10).map((row) => (
                                                          <tr key={row.institution_code} className="border-b border-slate-100 last:border-b-0">
                                                            <td className="px-3 py-2 font-hebrew text-slate-800">{row.institution_name || '—'}</td>
                                                            <td className="px-3 py-2 text-slate-600 text-xs">{row.institution_code}</td>
                                                            <td className="px-3 py-2 text-slate-700 font-hebrew">{row.prev_students}</td>
                                                            <td className="px-3 py-2 text-slate-700 font-hebrew">{row.curr_students}</td>
                                                            <td className={`px-3 py-2 font-bold font-hebrew ${row.delta_students < 0 ? 'text-red-700' : row.delta_students > 0 ? 'text-emerald-700' : 'text-slate-500'}`}>
                                                              {row.delta_students >= 0 ? '+' : ''}{row.delta_students}
                                                            </td>
                                                          </tr>
                                                        ))}
                                                      </tbody>
                                                    </table>
                                                  </div>
                                                )}
                                              </div>
                                            )}
                                          </div>
                                        );
                                      })()}

                                      {/* Phase 3.3: Route-level transportation audit — topics 52/140 only. */}
                                      {(topicCode === '52' || topicCode === '140') && (() => {
                                        const auditState = transportAudit[topicCode];
                                        const isAuditOpen = auditState?.expanded;
                                        const ta = auditState?.data;
                                        return (
                                          <div className="mt-4 border-t border-slate-200 pt-4">
                                            <button
                                              type="button"
                                              onClick={() => toggleTransportAudit(topicCode)}
                                              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-hebrew bg-white border border-sky-300 rounded-lg hover:bg-sky-50 transition"
                                            >
                                              <span>{isAuditOpen ? '▼' : '▶'}</span>
                                              <span>פירוט מסלולי הסעה — לפי מסלול, חברה, ורכב</span>
                                              {auditState?.loading && (
                                                <span className="w-4 h-4 border-2 border-sky-500 border-t-transparent rounded-full animate-spin" />
                                              )}
                                            </button>

                                            {isAuditOpen && auditState?.error && (
                                              <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm font-hebrew text-red-700">
                                                {auditState.error}
                                              </div>
                                            )}

                                            {isAuditOpen && ta && (
                                              <div className="mt-4 space-y-4">
                                                <div className="p-4 bg-gradient-to-l from-sky-50 to-white border border-sky-200 rounded-lg">
                                                  <div className="flex flex-wrap items-baseline gap-4 font-hebrew text-sm">
                                                    <div className="text-slate-600">
                                                      סה״כ מסלולים:{' '}
                                                      <span className="font-bold text-slate-900">{ta.summary.route_count_curr}</span>
                                                      {ta.summary.new_routes > 0 && (
                                                        <span className="mr-2 text-emerald-700">• {ta.summary.new_routes} חדשים</span>
                                                      )}
                                                      {ta.summary.dropped_routes > 0 && (
                                                        <span className="mr-2 text-red-700">• {ta.summary.dropped_routes} הוסרו</span>
                                                      )}
                                                    </div>
                                                    <div className="text-slate-600">
                                                      עלות מחושבת:{' '}
                                                      <span className="font-bold text-slate-900">{formatShekelText(ta.summary.curr_total)}</span>
                                                    </div>
                                                    <div className="text-slate-600">
                                                      שינוי:{' '}
                                                      <span className={`font-bold ${ta.summary.delta_total < 0 ? 'text-red-700' : ta.summary.delta_total > 0 ? 'text-emerald-700' : 'text-slate-500'}`}>
                                                        {ta.summary.delta_total >= 0 ? '+' : ''}
                                                        {formatShekelText(ta.summary.delta_total)}
                                                      </span>
                                                    </div>
                                                  </div>
                                                </div>

                                                {ta.by_company.length > 0 && (
                                                  <div className="overflow-x-auto border border-slate-200 rounded-lg bg-white">
                                                    <div className="px-3 py-2 bg-slate-50 border-b border-slate-200 font-hebrew text-xs text-slate-700 font-bold">
                                                      סיכום לפי חברת הסעה
                                                    </div>
                                                    <table className="w-full text-sm text-right">
                                                      <thead className="bg-slate-50 border-b border-slate-200">
                                                        <tr className="font-hebrew text-xs text-slate-600">
                                                          <th className="px-3 py-2 font-bold">חברה</th>
                                                          <th className="px-3 py-2 font-bold">מסלולים</th>
                                                          <th className="px-3 py-2 font-bold">עלות קודמת</th>
                                                          <th className="px-3 py-2 font-bold">עלות נוכחית</th>
                                                          <th className="px-3 py-2 font-bold">Δ</th>
                                                        </tr>
                                                      </thead>
                                                      <tbody>
                                                        {ta.by_company.map((c) => (
                                                          <tr key={c.company_code} className="border-b border-slate-100 last:border-b-0">
                                                            <td className="px-3 py-2 font-hebrew text-slate-800">
                                                              {c.company_name}
                                                              <span className="mr-2 text-xs text-slate-400">({c.company_code})</span>
                                                            </td>
                                                            <td className="px-3 py-2 text-slate-700 font-hebrew">{c.route_count}</td>
                                                            <td className="px-3 py-2 text-slate-700 font-hebrew">{formatShekelText(c.prev_total)}</td>
                                                            <td className="px-3 py-2 text-slate-900 font-hebrew font-bold">{formatShekelText(c.curr_total)}</td>
                                                            <td className={`px-3 py-2 font-bold font-hebrew ${c.delta_total < 0 ? 'text-red-700' : c.delta_total > 0 ? 'text-emerald-700' : 'text-slate-500'}`}>
                                                              {c.delta_total >= 0 ? '+' : ''}{formatShekelText(c.delta_total)}
                                                            </td>
                                                          </tr>
                                                        ))}
                                                      </tbody>
                                                    </table>
                                                  </div>
                                                )}

                                                {ta.by_vehicle.length > 0 && (
                                                  <div className="overflow-x-auto border border-slate-200 rounded-lg bg-white">
                                                    <div className="px-3 py-2 bg-slate-50 border-b border-slate-200 font-hebrew text-xs text-slate-700 font-bold">
                                                      סיכום לפי סוג רכב
                                                    </div>
                                                    <table className="w-full text-sm text-right">
                                                      <thead className="bg-slate-50 border-b border-slate-200">
                                                        <tr className="font-hebrew text-xs text-slate-600">
                                                          <th className="px-3 py-2 font-bold">סוג רכב</th>
                                                          <th className="px-3 py-2 font-bold">מסלולים</th>
                                                          <th className="px-3 py-2 font-bold">עלות נוכחית</th>
                                                          <th className="px-3 py-2 font-bold">Δ</th>
                                                        </tr>
                                                      </thead>
                                                      <tbody>
                                                        {ta.by_vehicle.map((v) => (
                                                          <tr key={v.vehicle_type} className="border-b border-slate-100 last:border-b-0">
                                                            <td className="px-3 py-2 font-hebrew text-slate-800">{v.vehicle_type}</td>
                                                            <td className="px-3 py-2 text-slate-700 font-hebrew">{v.route_count}</td>
                                                            <td className="px-3 py-2 text-slate-900 font-hebrew font-bold">{formatShekelText(v.curr_total)}</td>
                                                            <td className={`px-3 py-2 font-bold font-hebrew ${v.delta_total < 0 ? 'text-red-700' : v.delta_total > 0 ? 'text-emerald-700' : 'text-slate-500'}`}>
                                                              {v.delta_total >= 0 ? '+' : ''}{formatShekelText(v.delta_total)}
                                                            </td>
                                                          </tr>
                                                        ))}
                                                      </tbody>
                                                    </table>
                                                  </div>
                                                )}

                                                {ta.routes.length > 0 && (
                                                  <div className="overflow-x-auto border border-slate-200 rounded-lg bg-white">
                                                    <div className="px-3 py-2 bg-slate-50 border-b border-slate-200 font-hebrew text-xs text-slate-700 font-bold">
                                                      מסלולים — {Math.min(ta.routes.length, 25)} מובילים לפי שינוי
                                                    </div>
                                                    <table className="w-full text-sm text-right">
                                                      <thead className="bg-slate-50 border-b border-slate-200">
                                                        <tr className="font-hebrew text-xs text-slate-600">
                                                          <th className="px-3 py-2 font-bold">מסלול</th>
                                                          <th className="px-3 py-2 font-bold">כיוון</th>
                                                          <th className="px-3 py-2 font-bold">חברה</th>
                                                          <th className="px-3 py-2 font-bold">רכב</th>
                                                          <th className="px-3 py-2 font-bold">ימים</th>
                                                          <th className="px-3 py-2 font-bold">ק״מ</th>
                                                          <th className="px-3 py-2 font-bold">עלות יומית</th>
                                                          <th className="px-3 py-2 font-bold">השתתפות</th>
                                                          <th className="px-3 py-2 font-bold">חודשים</th>
                                                          <th className="px-3 py-2 font-bold">עלות נוכחית</th>
                                                          <th className="px-3 py-2 font-bold">Δ</th>
                                                          <th className="px-3 py-2 font-bold">מצב</th>
                                                        </tr>
                                                      </thead>
                                                      <tbody>
                                                        {ta.routes.slice(0, 25).map((r, i) => (
                                                          <tr
                                                            key={`${r.route_number}-${r.direction}-${r.vehicle_code}-${i}`}
                                                            className={`border-b border-slate-100 last:border-b-0 ${r.status === 'new' ? 'bg-emerald-50/40' : r.status === 'dropped' ? 'bg-red-50/40' : ''}`}
                                                          >
                                                            <td className="px-3 py-2 font-hebrew text-slate-800 font-bold">{r.route_number || '—'}</td>
                                                            <td className="px-3 py-2 font-hebrew text-slate-700">{r.direction || '—'}</td>
                                                            <td className="px-3 py-2 font-hebrew text-slate-700 max-w-[10rem] truncate" title={r.company_name}>{r.company_name || '—'}</td>
                                                            <td className="px-3 py-2 font-hebrew text-slate-700 max-w-[10rem] truncate" title={r.vehicle_type}>{r.vehicle_type || '—'}</td>
                                                            <td className="px-3 py-2 text-slate-700 font-hebrew">{r.days ?? '—'}</td>
                                                            <td className="px-3 py-2 text-slate-700 font-hebrew">{r.km_per_trip != null ? r.km_per_trip.toFixed(2) : '—'}</td>
                                                            <td className="px-3 py-2 text-slate-700 font-hebrew">{r.daily_cost != null ? formatShekelText(r.daily_cost) : '—'}</td>
                                                            <td className="px-3 py-2 text-slate-700 font-hebrew">{r.participation_pct != null ? `${(r.participation_pct * 100).toFixed(0)}%` : '—'}</td>
                                                            <td className="px-3 py-2 text-slate-600 font-hebrew text-xs">{r.curr_month_count || 0}</td>
                                                            <td className="px-3 py-2 text-slate-900 font-hebrew font-bold whitespace-nowrap">{formatShekelText(r.curr_total)}</td>
                                                            <td className={`px-3 py-2 font-bold font-hebrew whitespace-nowrap ${r.delta_total < 0 ? 'text-red-700' : r.delta_total > 0 ? 'text-emerald-700' : 'text-slate-500'}`}>
                                                              {r.delta_total >= 0 ? '+' : ''}{formatShekelText(r.delta_total)}
                                                            </td>
                                                            <td className="px-3 py-2 font-hebrew text-xs">
                                                              {r.status === 'new' && <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded">חדש</span>}
                                                              {r.status === 'dropped' && <span className="px-2 py-0.5 bg-red-100 text-red-800 rounded">הוסר</span>}
                                                              {r.status === 'changed' && <span className="px-2 py-0.5 bg-amber-100 text-amber-800 rounded">שונה</span>}
                                                              {r.status === 'unchanged' && <span className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded">ללא שינוי</span>}
                                                            </td>
                                                          </tr>
                                                        ))}
                                                      </tbody>
                                                    </table>
                                                  </div>
                                                )}
                                              </div>
                                            )}
                                          </div>
                                        );
                                      })()}
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    );
                  })
                ) : (
                  <div className="px-6 py-12 text-center text-neutral-600 font-hebrew">אין פריטים פעילים לחודש זה</div>
                )}
              </div>

              <div className="px-8 py-6 bg-gradient-to-r from-slate-100 to-slate-50 border-t-2 border-slate-300">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <h3 className="font-hebrew font-bold text-lg text-slate-900">סיכום מוצג</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 md:gap-6 text-right">
                    <div>
                      <p className="text-xs text-slate-600 font-hebrew">סה"כ מגיע (שורות מוצגות)</p>
                      <p className="font-bold text-xl text-slate-900"><ShekelAmount amount={displayedRowsTotal} mode={concreteRoundingMode} /></p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-600 font-hebrew">סה"כ שולם</p>
                      <p className="font-bold text-xl text-green-900"><ShekelAmount amount={paidTotal} mode={concreteRoundingMode} /></p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-600 font-hebrew">סה"כ פער (מגיע פחות שולם)</p>
                      <p className={`font-bold text-xl ${gapTotal < 0 ? 'text-red-900' : 'text-indigo-900'}`}>
                        <ShekelAmount amount={gapTotal} mode={concreteRoundingMode} />
                      </p>
                      {hasRoundingResidual && (
                        <p className="text-xs text-slate-500 font-hebrew mt-1">ייתכנו סטיות עיגול בסכומים הכלליים</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      <ExplanationEditModal
        isOpen={!!editingTopicCode}
        municipalityId={Number(id)}
        month={selectedMonth}
        topicCode={editingTopicCode}
        topicName={editingTopicName}
        currentExplanation={editingTopicCode ? explanations[editingTopicCode] : ''}
        onClose={handleExplanationModalClose}
        onSave={handleExplanationSave}
      />
    </PageWrapper>
  );
}
