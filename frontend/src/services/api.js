import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token') || localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      if (config.url?.includes('suggestions') || config.url?.includes('explanations')) {
        console.log('נ” API Token being sent:', {
          endpoint: config.url,
          method: config.method,
          hasToken: !!token,
          tokenLength: token.length,
          authorization: `Bearer ${token.substring(0, 20)}...`
        });
      }
    } else if (config.url?.includes('suggestions') || config.url?.includes('explanations')) {
      console.warn('ג ן¸ No token found in localStorage for API call:', config.url);
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Handle token expiry / 401 errors
apiClient.interceptors.response.use(
  (response) => {
    if (response.config?.url?.includes('explanations')) {
      console.log('נ“¡ API Response from explanations:', {
        url: response.config.url,
        method: response.config.method,
        status: response.status,
        dataKeys: Object.keys(response.data || {})
      });
    }
    return response;
  },
  (error) => {
    if (error.config?.url?.includes('explanations')) {
      console.error('ג API Error from explanations:', {
        url: error.config?.url,
        method: error.config?.method,
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data,
        message: error.message
      });
    }
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('access_token');
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  // Login
  login: (email, password) =>
    apiClient.post('/api/auth/login', { email, password }),

  // Get current user
  getCurrentUser: () =>
    apiClient.get('/api/auth/me'),
};

export const budgetAPI = {
  // Get budget for a specific month
  getBudgetMonth: (municipalityId, month) =>
    apiClient.get(`/api/budget/${municipalityId}/${month}`),

  // Get budget history
  getBudgetHistory: (municipalityId, months = 6) =>
    apiClient.get(`/api/budget/${municipalityId}/history/${months}`),

  // Get anomalies
  getAnomalies: (municipalityId, month) =>
    apiClient.get(`/api/budget/${municipalityId}/${month}/anomalies`),

  // Export to CSV
  exportBudgetCSV: (municipalityId, month) =>
    apiClient.get(`/api/export/budget/${municipalityId}/${month}/csv`, {
      responseType: 'blob',
    }),

  // Export history to CSV
  exportHistoryCSV: (municipalityId) =>
    apiClient.get(`/api/export/budget/${municipalityId}/history/csv`, {
      responseType: 'blob',
    }),

  // Institution drill-down for one topic code in a run
  getTopicInstitutions: (runId, municipalityId, topicCode) =>
    apiClient.get(`/api/budget/runs/${runId}/municipalities/${municipalityId}/institutions`, {
      params: { topic_code: topicCode },
    }),

  // Phase 3.1: expanded per-line drill-down for one topic code
  // Returns every BudgetLine row (gy / sharatim / mutavim / yadaniim /
  // moadon / sacal / ...) that rolls up into the topic's aggregate.
  getTopicLines: (runId, municipalityId, topicCode) =>
    apiClient.get(
      `/api/budget/runs/${runId}/municipalities/${municipalityId}/topic-lines/${topicCode}`
    ),

  // Institution drill-down for all high-school codes in a run
  getHighSchoolBreakdown: (runId, municipalityId) =>
    apiClient.get(`/api/budget/runs/${runId}/municipalities/${municipalityId}/high-school-breakdown`),

  // Student-count delta engine ג€” per-line count movement + driver classification
  getStudentCountDeltas: (runId, municipalityId) =>
    apiClient.get(`/api/budget/runs/${runId}/student-count-deltas`, {
      params: { municipality_id: municipalityId },
    }),

  // Priority 2: per-topic summary for one run (denormalised dashboard cache)
  getTopicSummaries: (runId) =>
    apiClient.get(`/api/budget/runs/${runId}/topic-summaries`),

  // Priority 3: per-month history for one (muni, topic_code) — sparkline data
  getCodeHistory: (municipalityId, topicCode) =>
    apiClient.get(`/api/budget/municipalities/${municipalityId}/topic-history/${topicCode}`),

  // Priority 4: anomalies list for one run + ack endpoint
  getCodeAnomalies: (runId) =>
    apiClient.get(`/api/budget/runs/${runId}/code-anomalies`),
  acknowledgeAnomaly: (anomalyId) =>
    apiClient.post(`/api/budget/code-anomalies/${anomalyId}/acknowledge`),
};

export const exportAPI = {
  // Admin: export monthly summary across all municipalities to Excel
  exportMonthlySummaryExcel: (month) =>
    apiClient.get(`/api/export/excel/${month}`, {
      responseType: 'blob',
    }),
};

export const municipalityAPI = {
  // Get all municipalities
  getAll: () =>
    apiClient.get('/api/municipalities/'),

  // Get specific municipality
  getById: (id) =>
    apiClient.get(`/api/municipalities/${id}/`),
};

export const runsAPI = {
  // Get all runs with optional filtering
  getAll: (params = {}) =>
    apiClient.get('/api/runs', { params }),

  // Get distinct months that have uploaded runs (newest first)
  getAvailableMonths: (params = {}) =>
    apiClient.get('/api/runs/available-months', { params }),

  // Get runs for a municipality
  getByMunicipality: (municipalityId) =>
    apiClient.get(`/api/runs/municipality/${municipalityId}`),

  // Get run for specific month
  getByMonth: (municipalityId, month) =>
    apiClient.get(`/api/runs/municipality/${municipalityId}/${month}`),

  // Admin: update CPA review status for a monthly run
  updateReviewStatus: (runId, status, note = '') =>
    apiClient.patch(`/api/admin/runs/${runId}/review-status`, { status, note }),
};

export const uploadAPI = {
  // Upload budget file
  uploadFile: (file, formData) =>
    apiClient.post('/api/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }),
};

export const explanationsAPI = {
  // Get detailed explanation for a single budget line (with change detection)
  getExplanation: (municipalityId, month, topicCode) =>
    apiClient.get(`/api/explanations/${municipalityId}/${month}/${topicCode}`),

  // Get all custom explanations for a month (legacy)
  getMonthExplanations: (municipalityId, month) =>
    apiClient.get(`/api/explanations/municipality/${municipalityId}/month/${month}`),

  // Get all explanations for a month (new detailed version with changes)
  getMonthExplanationsDetailed: (municipalityId, month) =>
    apiClient.get(`/api/explanations/municipality/${municipalityId}/month/${month}`),

  // Save custom explanation
  saveExplanation: (municipalityId, month, topicCode, customText) =>
    apiClient.post(`/api/explanations/${municipalityId}/${month}/${topicCode}`, {
      custom_text: customText,
    }),

  // Save custom explanation (alias)
  saveCustomExplanation: (municipalityId, month, topicCode, customText) =>
    apiClient.post(`/api/explanations/${municipalityId}/${month}/${topicCode}`, {
      custom_text: customText,
    }),

  // Delete custom explanation
  deleteExplanation: (municipalityId, month, topicCode) =>
    apiClient.delete(`/api/explanations/${municipalityId}/${month}/${topicCode}`),

  // Delete custom explanation (alias)
  deleteCustomExplanation: (municipalityId, month, topicCode) =>
    apiClient.delete(`/api/explanations/${municipalityId}/${month}/${topicCode}`),
};

export const presetsAPI = {
  // Get all presets (optionally filtered by topic_code)
  getAll: (topicCode = null) => {
    const params = topicCode ? { topic_code: topicCode } : {};
    return apiClient.get('/api/presets', { params });
  },

  // Get presets for a topic code
  getByTopic: (topicCode) =>
    apiClient.get('/api/presets', { params: { topic_code: topicCode } }),

  // Create new preset (admin only)
  create: (data) =>
    apiClient.post('/api/presets', data),

  // Update preset (admin only)
  update: (presetId, data) =>
    apiClient.patch(`/api/presets/${presetId}`, data),

  // Delete preset (admin only)
  delete: (presetId) =>
    apiClient.delete(`/api/presets/${presetId}`),
};

export const suggestionsAPI = {
  // Submit new suggestion
  submit: (data) =>
    apiClient.post('/api/suggestions', data),

  // Get pending suggestions (admin only)
  getPending: (params = {}) =>
    apiClient.get('/api/suggestions/pending', { params }),

  // Get count of pending suggestions (admin only)
  getPendingCount: () =>
    apiClient.get('/api/suggestions/pending/count'),

  // Get my suggestions (employee)
  getMy: () =>
    apiClient.get('/api/suggestions/my'),

  // Get my rejected suggestions (employee)
  getMyRejected: () =>
    apiClient.get('/api/suggestions/my-rejected'),

  // Get counts by status (employee)
  getMyCounts: () =>
    apiClient.get('/api/suggestions/my-counts'),

  // Get ALL my suggestions with statuses (employee)
  getMyAll: () =>
    apiClient.get('/api/suggestions/my-all'),

  // Approve suggestion (admin only)
  approve: (suggestionId, note = '') =>
    apiClient.patch(`/api/suggestions/${suggestionId}/approve`, { review_note: note }),

  // Reject suggestion (admin only)
  reject: (suggestionId, data) =>
    apiClient.patch(`/api/suggestions/${suggestionId}/reject`, data),
};

export const employeesAPI = {
  // Get all employees (admin only)
  getAll: (params = {}) =>
    apiClient.get('/api/employees', { params }),

  // Get specific employee (admin only)
  getById: (employeeId) =>
    apiClient.get(`/api/employees/${employeeId}`),

  // Create new employee (admin only)
  create: (data) =>
    apiClient.post('/api/employees', data),

  // Update employee (admin only)
  update: (employeeId, data) =>
    apiClient.patch(`/api/employees/${employeeId}`, data),

  // Deactivate employee (admin only)
  delete: (employeeId) =>
    apiClient.delete(`/api/employees/${employeeId}`),
};

export const reasonsAPI = {
  // Get all active reasons (with optional filters)
  getAll: (params = {}) =>
    apiClient.get('/api/reasons', { params }),

  // Get reasons by category
  getByCategory: (category) =>
    apiClient.get('/api/reasons', { params: { category } }),

  // Get reasons for a topic code (with smart filtering)
  getForTopic: (topicCode, direction = null) => {
    const params = { topic_code: topicCode };
    if (direction) params.direction = direction;
    return apiClient.get('/api/reasons', { params });
  },

  // Get specific reason
  getById: (reasonId) =>
    apiClient.get(`/api/reasons/${reasonId}`),

  // Search reasons by title (substring match)
  search: (query) =>
    apiClient.get('/api/reasons', { params: { search: query } }),

  // Create new reason (admin/CPA only)
  create: (data) =>
    apiClient.post('/api/reasons', data),

  // Update reason (admin/CPA only)
  update: (reasonId, data) =>
    apiClient.patch(`/api/reasons/${reasonId}`, data),

  // Deactivate reason (admin/CPA only)
  delete: (reasonId) =>
    apiClient.delete(`/api/reasons/${reasonId}`),
};

export const positionsAPI = {
  // Get positions & quotas analysis for municipality + month
  getAnalysis: (municipalityId, month) =>
    apiClient.get(`/api/positions/analysis/${municipalityId}/${month}`),
  // Admin: full summary for all municipalities for a given month
  getAdminSummary: (month) =>
    apiClient.get(`/api/positions/admin-summary/${month}`),
};

export const deadlinesAPI = {
  // Get all ministry deadlines + application status for a municipality
  getDeadlines: (municipalityId, year) => {
    const params = year ? `?year=${year}` : '';
    return apiClient.get(`/api/deadlines/${municipalityId}${params}`);
  },
  // Update application tracking for a deadline
  updateApplication: (municipalityId, deadlineId, data) =>
    apiClient.post(`/api/deadlines/${municipalityId}/${deadlineId}/application`, data),
  // Get gap history for a position type
  getGapHistory: (municipalityId, positionType) =>
    apiClient.get(`/api/positions/gaps-history/${municipalityId}/${positionType}`),
  // Get priority scores for all gaps
  getPriority: (municipalityId, month) =>
    apiClient.get(`/api/positions/priority/${municipalityId}/${month}`),
  // Admin: overview of all municipalities deadline statuses
  getAdminOverview: () =>
    apiClient.get('/api/deadlines/admin/overview'),
};

export const analyticsAPI = {
  getTrends: (municipalityId) =>
    apiClient.get(`/api/analytics/trends/${municipalityId}`),
  getYearComparison: (municipalityId, month) =>
    apiClient.get(`/api/analytics/year-comparison/${municipalityId}/${month}`),
  getForecast: (municipalityId) =>
    apiClient.get(`/api/analytics/forecast/${municipalityId}`),
  getAnomalies: (municipalityId, month) =>
    apiClient.get(`/api/analytics/anomalies/${municipalityId}/${month}`),
  getRetroAging: (municipalityId, month) =>
    apiClient.get(`/api/analytics/retro-aging/${municipalityId}/${month}`),
  getAdminOverview: (month) =>
    apiClient.get(`/api/analytics/overview/${month}`),
  getYtd: (municipalityId, month, fiscalStartMonth = 1) =>
    apiClient.get(
      `/api/analytics/ytd/${municipalityId}/${month}`,
      { params: { fiscal_start_month: fiscalStartMonth } },
    ),
  getVarianceDrivers: (municipalityId, month, limit = 10) =>
    apiClient.get(
      `/api/analytics/variance-drivers/${municipalityId}/${month}`,
      { params: { limit } },
    ),
  getExplainedCoverage: (municipalityId, month) =>
    apiClient.get(`/api/analytics/explained-coverage/${municipalityId}/${month}`),
  getTieOut: (municipalityId, month) =>
    apiClient.get(`/api/analytics/tie-out/${municipalityId}/${month}`),
  getPeerBenchmark: (municipalityId, month, includeTest = false) =>
    apiClient.get(
      `/api/analytics/peer-benchmark/${municipalityId}/${month}`,
      { params: { include_test: includeTest } },
    ),
  getFormulaVariance: (municipalityId, month) =>
    apiClient.get(`/api/analytics/formula-variance/${municipalityId}/${month}`),
  getFormulaDrivers: (runId, topicCode) =>
    apiClient.get(`/api/analytics/formula-drivers/${runId}/${topicCode}`),
  getTransportRoutes: (runId, topicCode, params = {}) =>
    apiClient.get(
      `/api/analytics/transport-routes/${runId}/${topicCode}`,
      { params },
    ),
};

export const reportsAPI = {
  // Get list of reports for a municipality
  list: (municipalityId) =>
    apiClient.get(`/api/reports/list/${municipalityId}`),

  // Download a report (blob response)
  download: (reportId) =>
    apiClient.get(`/api/reports/download/${reportId}`, { responseType: 'blob' }),

  // Generate monthly report (returns job_id)
  generate: (municipalityId, month) =>
    apiClient.post(`/api/reports/generate/${municipalityId}/${month}`),

  // Generate comparison report (returns job_id)
  generateComparison: (municipalityId) =>
    apiClient.post(`/api/reports/generate/comparison/${municipalityId}`),

  // Poll job status
  getStatus: (jobId) =>
    apiClient.get(`/api/reports/status/${jobId}`),

  // Delete a report (admin)
  delete: (reportId) =>
    apiClient.delete(`/api/reports/${reportId}`),

  // Admin: all reports
  adminAll: () =>
    apiClient.get('/api/reports/admin/all'),

  // Branding
  getBranding: () =>
    apiClient.get('/api/reports/branding'),

  saveBranding: (formData) =>
    apiClient.post('/api/reports/branding', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  deleteLogo: () =>
    apiClient.delete('/api/reports/branding/logo'),

  // Templates
  getTemplates: () =>
    apiClient.get('/api/reports/templates'),

  createTemplate: (data) =>
    apiClient.post('/api/reports/templates', data),

  deleteTemplate: (templateId) =>
    apiClient.delete(`/api/reports/templates/${templateId}`),
};

export const remindersAPI = {
  // All ministry deadlines (sorted by urgency)
  getDeadlines: () =>
    apiClient.get('/api/reminders/deadlines'),

  // Upcoming reminders for municipality (next 90 days)
  getUpcoming: (municipalityId) =>
    apiClient.get(`/api/reminders/upcoming/${municipalityId}`),

  // Full calendar of reminders
  getCalendar: (municipalityId) =>
    apiClient.get(`/api/reminders/calendar/${municipalityId}`),

  // Dismiss a reminder
  dismiss: (reminderId) =>
    apiClient.post(`/api/reminders/dismiss/${reminderId}`),

  // Admin: all reminders with filters
  adminAll: (params = {}) =>
    apiClient.get('/api/reminders/admin/all', { params }),

  // Admin CRUD for deadlines
  createDeadline: (data) =>
    apiClient.post('/api/reminders/deadlines', data),

  updateDeadline: (id, data) =>
    apiClient.put(`/api/reminders/deadlines/${id}`, data),

  deleteDeadline: (id) =>
    apiClient.delete(`/api/reminders/deadlines/${id}`),

  // Settings
  getSettings: (municipalityId = null) =>
    apiClient.get('/api/reminders/settings', { params: municipalityId ? { municipality_id: municipalityId } : {} }),

  saveSettings: (data, municipalityId = null) =>
    apiClient.post('/api/reminders/settings', data, { params: municipalityId ? { municipality_id: municipalityId } : {} }),

  getAllMunicipalitySettings: () =>
    apiClient.get('/api/reminders/settings/all-municipalities'),
};

export const notificationsAPI = {
  // Get notifications for municipality
  getAll: (municipalityId, limit = 20) =>
    apiClient.get(`/api/notifications/${municipalityId}`, { params: { limit } }),

  // Unread count
  getUnreadCount: (municipalityId) =>
    apiClient.get(`/api/notifications/unread-count/${municipalityId}`),

  // Mark single as read
  markRead: (notificationId) =>
    apiClient.patch(`/api/notifications/${notificationId}/read`),

  // Mark all as read
  markAllRead: (municipalityId) =>
    apiClient.patch(`/api/notifications/read-all/${municipalityId}`),
};

// Ministry Integration API
export const ministryAPI = {
  // Code lookup
  getCodes: (params = {}) => apiClient.get('/api/ministry/codes', { params }),
  getCode: (code, userId = null) =>
    apiClient.get(`/api/ministry/codes/${code}`, { params: userId ? { user_id: userId } : {} }),
  getCategories: () => apiClient.get('/api/ministry/categories'),
  updateCode: (id, data) => apiClient.put(`/api/ministry/codes/${id}`, data),

  // Policy changes
  getPolicyChanges: (params = {}) => apiClient.get('/api/ministry/policy-changes', { params }),
  createPolicyChange: (data) => apiClient.post('/api/ministry/policy-changes', data),
  acknowledgeChange: (id, municipalityId) =>
    apiClient.patch(`/api/ministry/policy-changes/${id}/acknowledge`, null, {
      params: { municipality_id: municipalityId },
    }),
  deletePolicyChange: (id) => apiClient.delete(`/api/ministry/policy-changes/${id}`),
  getPolicyUnreadCount: (municipalityId) =>
    apiClient.get('/api/ministry/policy-changes/unread-count', {
      params: { municipality_id: municipalityId },
    }),

  // Circulars
  getCirculars: (params = {}) => apiClient.get('/api/ministry/circulars', { params }),
  createCircular: (data) => apiClient.post('/api/ministry/circulars', data),
  updateCircular: (id, data) => apiClient.put(`/api/ministry/circulars/${id}`, data),
  deleteCircular: (id) => apiClient.delete(`/api/ministry/circulars/${id}`),

  // Stats
  getStats: () => apiClient.get('/api/ministry/stats'),
};

export default apiClient;
