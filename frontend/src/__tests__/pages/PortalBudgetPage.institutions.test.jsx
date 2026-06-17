import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import PortalBudgetPage from '../../pages/PortalBudgetPage';

const mockGetBudgetMonth = vi.fn();
const mockGetCodes = vi.fn();
const mockGetMonthExplanations = vi.fn();
const mockGetTopicInstitutions = vi.fn();
const mockGetHighSchoolBreakdown = vi.fn();

vi.mock('../../context/AuthContext', () => ({
  useAuth: () => ({
    user: { municipality_id: 1, municipality_name: 'עיר בדיקה' },
  }),
}));

vi.mock('../../services/api', () => ({
  budgetAPI: {
    getBudgetMonth: (...args) => mockGetBudgetMonth(...args),
    getTopicInstitutions: (...args) => mockGetTopicInstitutions(...args),
    getHighSchoolBreakdown: (...args) => mockGetHighSchoolBreakdown(...args),
  },
  explanationsAPI: {
    getMonthExplanations: (...args) => mockGetMonthExplanations(...args),
  },
  suggestionsAPI: {
    submit: vi.fn(),
  },
  ministryAPI: {
    getCodes: (...args) => mockGetCodes(...args),
  },
}));

vi.mock('../../components/portal/PortalWrapper', () => ({
  default: ({ children }) => <div>{children}</div>,
}));

vi.mock('../../components/portal/SmartExplanationDisplay', () => ({
  default: () => <div data-testid="smart-explanation" />,
}));

vi.mock('../../components/portal/ExplanationSuggestionModal', () => ({
  default: () => null,
}));

vi.mock('../../components/review/ReviewStatusControl', () => ({
  default: () => null,
}));

vi.mock('../../components/common/RoundingModeToggle', () => ({
  default: () => null,
}));

vi.mock('../../components/common/RoundingDisclosureBanner', () => ({
  default: () => null,
}));

vi.mock('../../components/common/ShekelAmount', () => ({
  default: ({ amount }) => <span>{amount}</span>,
}));

vi.mock('../../utils/roundingMode', () => ({
  useRoundingMode: () => ['exact', vi.fn()],
}));

describe('PortalBudgetPage institution drill-down', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.pushState({}, '', '/portal-budget?month=2026-03&municipality=1');

    mockGetBudgetMonth.mockResolvedValue({
      data: {
        run_id: 10,
        invoice_total: 1000,
        breakdown_total: 1000,
        budget_lines: [
          {
            id: 1,
            topic_code: '361',
            budget_topic: 'חטיבה עליונה',
            amount: 1000,
            line_type: 'regular',
            is_retro: false,
          },
        ],
        month_changes: { changes_by_topic: {} },
      },
    });

    mockGetCodes.mockResolvedValue({
      data: [{ code: '361', category: 'חטיבה עליונה' }],
    });

    mockGetMonthExplanations.mockResolvedValue({ data: { explanations: [] } });
    mockGetTopicInstitutions.mockResolvedValue({
      data: {
        institutions: [
          { institution_code: 'A1', institution_name: 'תיכון א', amount: 1000, num_children: 100, participation_pct: 100 },
        ],
      },
    });
    mockGetHighSchoolBreakdown.mockResolvedValue({
      data: {
        topics: {
          '361': {
            institutions: [{ institution_code: 'A1', institution_name: 'תיכון א', amount: 1000 }],
          },
        },
      },
    });
  });

  it('requests topic institution breakdown when clicking row drill-down', async () => {
    render(
      <MemoryRouter>
        <PortalBudgetPage />
      </MemoryRouter>
    );

    const topicButton = await screen.findByText(/פירוט לפי מוסד/);
    fireEvent.click(topicButton);

    await waitFor(() => {
      expect(mockGetTopicInstitutions).toHaveBeenCalledWith(10, 1, '361');
    });
  });

  it('requests all high-school breakdown when clicking category drill-down', async () => {
    render(
      <MemoryRouter>
        <PortalBudgetPage />
      </MemoryRouter>
    );

    const categoryButton = await screen.findByText(/פירוט כל התיכון/);
    fireEvent.click(categoryButton);

    await waitFor(() => {
      expect(mockGetHighSchoolBreakdown).toHaveBeenCalledWith(10, 1);
    });
  });
});
