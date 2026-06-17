import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import axios from 'axios';

// Mock axios before the module is loaded
vi.mock('axios', () => {
  const mockAxiosInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  };
  return {
    default: {
      create: vi.fn(() => mockAxiosInstance),
      ...mockAxiosInstance,
    },
  };
});

// Import after mock is set up
import { authAPI, budgetAPI, municipalityAPI, suggestionsAPI, employeesAPI, runsAPI } from '../../services/api';

describe('API service modules', () => {
  let mockClient;

  beforeEach(() => {
    // Get the mocked axios instance
    mockClient = axios.create();
    vi.clearAllMocks();
  });

  // ── authAPI ────────────────────────────────────────────────────────────────

  describe('authAPI.login', () => {
    it('calls POST /api/auth/login with email and password', async () => {
      mockClient.post.mockResolvedValue({ data: { access_token: 'abc123' } });
      await authAPI.login('user@test.com', 'password123');
      expect(mockClient.post).toHaveBeenCalledWith(
        '/api/auth/login',
        { email: 'user@test.com', password: 'password123' }
      );
    });
  });

  describe('authAPI.getCurrentUser', () => {
    it('calls GET /api/auth/me', async () => {
      mockClient.get.mockResolvedValue({ data: { id: 1, email: 'user@test.com' } });
      await authAPI.getCurrentUser();
      expect(mockClient.get).toHaveBeenCalledWith('/api/auth/me');
    });
  });

  // ── budgetAPI ──────────────────────────────────────────────────────────────

  describe('budgetAPI.getBudgetMonth', () => {
    it('calls GET /api/budget/{municipalityId}/{month}', async () => {
      mockClient.get.mockResolvedValue({ data: {} });
      await budgetAPI.getBudgetMonth(4, '2026-03');
      expect(mockClient.get).toHaveBeenCalledWith('/api/budget/4/2026-03');
    });
  });

  describe('budgetAPI.getBudgetHistory', () => {
    it('calls GET with default 6 months', async () => {
      mockClient.get.mockResolvedValue({ data: [] });
      await budgetAPI.getBudgetHistory(4);
      expect(mockClient.get).toHaveBeenCalledWith('/api/budget/4/history/6');
    });

    it('calls GET with custom month count', async () => {
      mockClient.get.mockResolvedValue({ data: [] });
      await budgetAPI.getBudgetHistory(4, 12);
      expect(mockClient.get).toHaveBeenCalledWith('/api/budget/4/history/12');
    });
  });

  describe('budgetAPI.getAnomalies', () => {
    it('calls GET /api/budget/{id}/{month}/anomalies', async () => {
      mockClient.get.mockResolvedValue({ data: [] });
      await budgetAPI.getAnomalies(4, '2026-03');
      expect(mockClient.get).toHaveBeenCalledWith('/api/budget/4/2026-03/anomalies');
    });
  });

  describe('budgetAPI.getTopicInstitutions', () => {
    it('calls GET topic institution breakdown endpoint with topic_code param', async () => {
      mockClient.get.mockResolvedValue({ data: {} });
      await budgetAPI.getTopicInstitutions(11, 4, '361');
      expect(mockClient.get).toHaveBeenCalledWith(
        '/api/budget/runs/11/municipalities/4/institutions',
        { params: { topic_code: '361' } }
      );
    });
  });

  describe('budgetAPI.getHighSchoolBreakdown', () => {
    it('calls GET all high-school breakdown endpoint', async () => {
      mockClient.get.mockResolvedValue({ data: {} });
      await budgetAPI.getHighSchoolBreakdown(11, 4);
      expect(mockClient.get).toHaveBeenCalledWith(
        '/api/budget/runs/11/municipalities/4/high-school-breakdown'
      );
    });
  });

  // ── suggestionsAPI ─────────────────────────────────────────────────────────

  describe('suggestionsAPI', () => {
    it('getPending calls GET /api/suggestions/pending', async () => {
      mockClient.get.mockResolvedValue({ data: [] });
      await suggestionsAPI.getPending();
      expect(mockClient.get).toHaveBeenCalledWith('/api/suggestions/pending', { params: {} });
    });

    it('getMy calls GET /api/suggestions/my', async () => {
      mockClient.get.mockResolvedValue({ data: [] });
      await suggestionsAPI.getMy();
      expect(mockClient.get).toHaveBeenCalledWith('/api/suggestions/my');
    });

    it('approve calls PATCH /api/suggestions/{id}/approve', async () => {
      mockClient.patch.mockResolvedValue({ data: {} });
      await suggestionsAPI.approve(7, 'OK');
      expect(mockClient.patch).toHaveBeenCalledWith(
        '/api/suggestions/7/approve',
        { review_note: 'OK' }
      );
    });

    it('reject calls PATCH /api/suggestions/{id}/reject', async () => {
      mockClient.patch.mockResolvedValue({ data: {} });
      await suggestionsAPI.reject(7, { review_note: 'Not valid' });
      expect(mockClient.patch).toHaveBeenCalledWith(
        '/api/suggestions/7/reject',
        { review_note: 'Not valid' }
      );
    });
  });

  describe('runsAPI', () => {
    it('updateReviewStatus calls PATCH /api/admin/runs/{id}/review-status', async () => {
      await runsAPI.updateReviewStatus(11, 'reviewed', 'done');
      expect(mockClient.patch).toHaveBeenCalledWith('/api/admin/runs/11/review-status', {
        status: 'reviewed',
        note: 'done',
      });
    });
  });

  // ── employeesAPI ───────────────────────────────────────────────────────────

  describe('employeesAPI', () => {
    it('getAll calls GET /api/employees', async () => {
      mockClient.get.mockResolvedValue({ data: [] });
      await employeesAPI.getAll();
      expect(mockClient.get).toHaveBeenCalledWith('/api/employees', { params: {} });
    });

    it('create calls POST /api/employees', async () => {
      const payload = { email: 'e@test.com', first_name: 'A', last_name: 'B', municipality_ids: [1] };
      mockClient.post.mockResolvedValue({ data: {} });
      await employeesAPI.create(payload);
      expect(mockClient.post).toHaveBeenCalledWith('/api/employees', payload);
    });

    it('update calls PATCH /api/employees/{id}', async () => {
      mockClient.patch.mockResolvedValue({ data: {} });
      await employeesAPI.update(5, { first_name: 'Updated' });
      expect(mockClient.patch).toHaveBeenCalledWith('/api/employees/5', { first_name: 'Updated' });
    });

    it('delete calls DELETE /api/employees/{id}', async () => {
      mockClient.delete.mockResolvedValue({ data: {} });
      await employeesAPI.delete(5);
      expect(mockClient.delete).toHaveBeenCalledWith('/api/employees/5');
    });
  });
});
