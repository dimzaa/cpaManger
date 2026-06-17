import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import StudentCountDeltaChip from '../../components/common/StudentCountDeltaChip';

describe('StudentCountDeltaChip', () => {
  it('renders nothing when delta is null', () => {
    const { container } = render(<StudentCountDeltaChip delta={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing when delta_children is zero and no variance_driver', () => {
    const delta = {
      delta_children: 0,
      variance_driver: null,
    };
    const { container } = render(<StudentCountDeltaChip delta={delta} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows +29 ילדים chip when count increased', () => {
    const delta = {
      prev_num_children: 100,
      curr_num_children: 129,
      delta_children: 29,
      delta_amount: 29000,
      explained_amount: 29000,
      explained_ratio: 1.0,
      variance_driver: 'student_count',
    };
    render(<StudentCountDeltaChip delta={delta} />);
    expect(screen.getByText(/\+29 ילדים/)).toBeInTheDocument();
  });

  it('shows -12 ילדים chip with red styling when count decreased', () => {
    const delta = {
      prev_num_children: 100,
      curr_num_children: 88,
      delta_children: -12,
      delta_amount: -12000,
      explained_amount: -12000,
      explained_ratio: 1.0,
      variance_driver: 'student_count',
    };
    render(<StudentCountDeltaChip delta={delta} />);
    const chip = screen.getByText(/-12 ילדים/);
    expect(chip).toBeInTheDocument();
    const wrapper = chip.closest('span.inline-flex');
    expect(wrapper.className).toMatch(/bg-red-50/);
  });

  it('shows formula_or_rate badge only when showDriverBadge is true', () => {
    const delta = {
      prev_num_children: 100,
      curr_num_children: 100,
      delta_children: 0,
      delta_amount: 10000,
      explained_amount: 0,
      explained_ratio: 0,
      variance_driver: 'formula_or_rate',
    };
    const { rerender } = render(<StudentCountDeltaChip delta={delta} />);
    expect(screen.queryByText('נוסחה/תעריף')).not.toBeInTheDocument();

    rerender(<StudentCountDeltaChip delta={delta} showDriverBadge />);
    expect(screen.getByText('נוסחה/תעריף')).toBeInTheDocument();
  });

  it('shows mixed badge when variance_driver is mixed', () => {
    const delta = {
      prev_num_children: 100,
      curr_num_children: 110,
      delta_children: 10,
      delta_amount: 20000,
      explained_amount: 10000,
      explained_ratio: 0.5,
      variance_driver: 'mixed',
    };
    render(<StudentCountDeltaChip delta={delta} showDriverBadge />);
    expect(screen.getByText('מעורב')).toBeInTheDocument();
  });

  it('puts Hebrew tooltip text on the wrapping span', () => {
    const delta = {
      prev_num_children: 100,
      curr_num_children: 120,
      delta_children: 20,
      delta_amount: 20000,
      explained_amount: 20000,
      explained_ratio: 1.0,
      variance_driver: 'student_count',
    };
    const { container } = render(<StudentCountDeltaChip delta={delta} />);
    const wrapper = container.querySelector('[title]');
    expect(wrapper).toBeTruthy();
    expect(wrapper.getAttribute('title')).toMatch(/מספר ילדים/);
    expect(wrapper.getAttribute('title')).toMatch(/100/);
    expect(wrapper.getAttribute('title')).toMatch(/120/);
  });

  it('picks the formula_or_rate tooltip when driver is formula_or_rate', () => {
    const delta = {
      prev_num_children: 100,
      curr_num_children: 100,
      delta_children: 0,
      delta_amount: 10000,
      explained_amount: 0,
      explained_ratio: 0,
      variance_driver: 'formula_or_rate',
    };
    const { container } = render(<StudentCountDeltaChip delta={delta} showDriverBadge />);
    const wrapper = container.querySelector('[title]');
    expect(wrapper.getAttribute('title')).toMatch(/נובע מגורם אחר/);
  });
});
