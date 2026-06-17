import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor, fireEvent, cleanup } from '@testing-library/react';
import ComparePage from '../../pages/ComparePage';

vi.mock('../../components/layout/PageWrapper', () => ({
  default: ({ children }) => <div>{children}</div>,
}));

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }) => <div>{children}</div>,
  BarChart: ({ children }) => <div>{children}</div>,
  Bar: () => <div />,
  XAxis: () => <div />,
  YAxis: () => <div />,
  CartesianGrid: () => <div />,
  Tooltip: () => <div />,
  Legend: () => <div />,
}));

vi.mock('../../services/api', () => ({
  municipalityAPI: {
    getAll: vi.fn(async () => ({ data: [{ id: 1, name: 'רשות א' }] })),
  },
  budgetAPI: {
    getBudgetMonth: vi.fn(async (_municipalityId, month) => {
      if (month === '2026-03') {
        return {
          data: {
            budget_lines: [{ id: 1, budget_topic: 'נושא', amount: 5_243_712 }],
          },
        };
      }
      return {
        data: {
          budget_lines: [{ id: 1, budget_topic: 'נושא', amount: 6_243_712 }],
        },
      };
    }),
  },
}));

describe('ComparePage executive rounding', () => {
  beforeEach(() => {
    localStorage.clear();
    cleanup();
  });

  it('re-renders amounts when mode changes and shows disclosure banner', async () => {
    render(<ComparePage />);

    const monthInputs = document.querySelectorAll('input[type="month"]');
    fireEvent.change(monthInputs[0], { target: { value: '2026-03' } });
    fireEvent.change(monthInputs[1], { target: { value: '2026-04' } });

    await waitFor(() => {
      expect(screen.getByText('₪ 5,243,712')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('אלפי'));

    await waitFor(() => {
      expect(screen.getByText('5,243.7 אלפי ₪')).toBeInTheDocument();
      expect(screen.getByText(/בסכומים באלפי ש״ח/)).toBeInTheDocument();
    });
  });

  it('persists mode across remount', async () => {
    const { unmount } = render(<ComparePage />);

    fireEvent.click(await screen.findByText('אלפי'));
    expect(localStorage.getItem('cpa.display.roundingMode')).toBe('thousands');

    unmount();
    render(<ComparePage />);
    expect(screen.getByText('אלפי').className).toContain('bg-slate-800');
  });
});
