import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ReviewStatusControl from '../../components/review/ReviewStatusControl';

function renderControl(props = {}) {
  const onPersist = props.onPersist || vi.fn().mockResolvedValue({});
  render(
    <ReviewStatusControl
      status="pending"
      note=""
      reviewerName=""
      reviewedAt=""
      editable
      onPersist={onPersist}
      {...props}
    />
  );
  return { onPersist };
}

describe('ReviewStatusControl', () => {
  it('renders correct label and color class for every status', () => {
    const statuses = [
      ['pending', 'ממתין לבדיקה', 'bg-slate-50'],
      ['in_review', 'בבדיקה', 'bg-blue-50'],
      ['reviewed', 'נבדק', 'bg-emerald-50'],
      ['flagged', 'דורש תשומת לב', 'bg-amber-50'],
    ];

    statuses.forEach(([status, label, className]) => {
      const { unmount } = render(
        <ReviewStatusControl
          status={status}
          editable={false}
          reviewerName=""
          reviewedAt=""
        />
      );
      const pill = screen.getByTestId('review-status-pill');
      expect(pill).toHaveTextContent(label);
      expect(pill.className).toContain(className);
      unmount();
    });
  });

  it('select change persists status and shows optimistic update', async () => {
    let resolvePersist;
    const onPersist = vi.fn(
      () =>
        new Promise((resolve) => {
          resolvePersist = resolve;
        })
    );
    renderControl({ onPersist });

    const user = userEvent.setup();
    const select = screen.getByTestId('review-status-select');
    await user.selectOptions(select, 'in_review');

    expect(screen.getByTestId('review-status-pill')).toHaveTextContent('בבדיקה');
    expect(onPersist).toHaveBeenCalledWith({ status: 'in_review', note: '' });

    resolvePersist({});
    await waitFor(() => {
      expect(screen.getByTestId('review-status-toast')).toHaveTextContent('✅');
    });
  });

  it('on persist failure reverts optimistic status', async () => {
    const onPersist = vi.fn().mockRejectedValue(new Error('boom'));
    renderControl({ onPersist });

    const user = userEvent.setup();
    const select = screen.getByTestId('review-status-select');
    await user.selectOptions(select, 'reviewed');

    expect(onPersist).toHaveBeenCalledWith({ status: 'reviewed', note: '' });

    await waitFor(() => {
      expect(screen.getByTestId('review-status-pill')).toHaveTextContent('ממתין לבדיקה');
    });
  });

  it('flagged requires note before persist', async () => {
    const onPersist = vi.fn().mockResolvedValue({});
    renderControl({ onPersist });

    const user = userEvent.setup();
    await user.selectOptions(screen.getByTestId('review-status-select'), 'flagged');

    expect(screen.getByTestId('flag-note-modal')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'שמירה' }));

    expect(onPersist).not.toHaveBeenCalled();
    expect(screen.getByText('חובה להזין הערה')).toBeInTheDocument();

    await user.type(screen.getByTestId('flag-note-input'), 'דורש בדיקה ידנית');
    await user.click(screen.getByRole('button', { name: 'שמירה' }));

    await waitFor(() => {
      expect(onPersist).toHaveBeenCalledWith({ status: 'flagged', note: 'דורש בדיקה ידנית' });
    });
  });

  it('portal-style read-only pill has no select and no persist click behavior', async () => {
    const onPersist = vi.fn();
    render(
      <ReviewStatusControl
        status="reviewed"
        reviewerName="בודק"
        reviewedAt="2026-04-01T10:00:00"
        editable={false}
        onPersist={onPersist}
      />
    );

    expect(screen.queryByTestId('review-status-select')).not.toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(screen.getByTestId('review-status-pill'));
    expect(onPersist).not.toHaveBeenCalled();
  });
});
