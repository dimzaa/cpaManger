import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import { useRoundingMode } from '../../utils/roundingMode';

function Probe() {
  const [mode, setMode] = useRoundingMode();
  return (
    <div>
      <span data-testid="mode">{mode}</span>
      <button onClick={() => setMode('thousands')}>set-thousands</button>
    </div>
  );
}

describe('useRoundingMode', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('defaults to exact', () => {
    render(<Probe />);
    expect(screen.getByTestId('mode').textContent).toBe('exact');
  });

  it('persists selected mode in localStorage', () => {
    render(<Probe />);
    fireEvent.click(screen.getByText('set-thousands'));
    expect(screen.getByTestId('mode').textContent).toBe('thousands');
    expect(localStorage.getItem('cpa.display.roundingMode')).toBe('thousands');
  });
});
