import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ShekelAmount from '../../components/common/ShekelAmount';
import { ROUNDING_MODES } from '../../utils/formatShekel';

describe('ShekelAmount', () => {
  it('shows exact value in title when rounded mode is active', () => {
    render(<ShekelAmount amount={12} mode={ROUNDING_MODES.THOUSANDS} />);
    const element = screen.getByText('0.0 אלפי ₪');
    expect(element).toHaveAttribute('title', '₪ 12');
  });

  it('does not add title in exact mode', () => {
    render(<ShekelAmount amount={5243712} mode={ROUNDING_MODES.EXACT} />);
    const element = screen.getByText('₪ 5,243,712');
    expect(element).not.toHaveAttribute('title');
  });
});
