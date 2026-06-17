import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import { AuthProvider, useAuth } from '../../context/AuthContext';

// Mock api module
vi.mock('../../services/api', () => ({
  authAPI: {
    login: vi.fn(),
    getCurrentUser: vi.fn(),
  },
}));

import { authAPI } from '../../services/api';

// Helper component to expose context values
function AuthConsumer() {
  const auth = useAuth();
  return (
    <div>
      <span data-testid="is-authenticated">{String(auth.isAuthenticated)}</span>
      <span data-testid="is-admin">{String(auth.isAdmin)}</span>
      <span data-testid="is-municipality">{String(auth.isMunicipality)}</span>
      <span data-testid="user-email">{auth.user?.email || 'none'}</span>
      <span data-testid="loading">{String(auth.loading)}</span>
      <span data-testid="error">{auth.error || 'none'}</span>
      <button onClick={() => auth.login('user@test.com', 'pass').catch(() => {})}>Login</button>
      <button onClick={auth.logout}>Logout</button>
    </div>
  );
}

function renderWithProvider() {
  return render(
    <AuthProvider>
      <AuthConsumer />
    </AuthProvider>
  );
}

describe('AuthProvider — initial state', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    renderWithProvider();
    expect(screen.getByTestId('is-authenticated')).toBeInTheDocument();
  });

  it('isAuthenticated is false when no token in localStorage', async () => {
    renderWithProvider();
    await waitFor(() => {
      expect(screen.getByTestId('is-authenticated').textContent).toBe('false');
    });
  });

  it('loading becomes false after mount', async () => {
    renderWithProvider();
    await waitFor(() => {
      expect(screen.getByTestId('loading').textContent).toBe('false');
    });
  });

  it('restores user from localStorage on mount', async () => {
    localStorage.setItem('token', 'tok123');
    localStorage.setItem('access_token', 'tok123');
    localStorage.setItem('user', JSON.stringify({ email: 'saved@test.com', role: 'admin' }));

    renderWithProvider();
    await waitFor(() => {
      expect(screen.getByTestId('user-email').textContent).toBe('saved@test.com');
    });
  });

  it('handles corrupt localStorage user gracefully', async () => {
    localStorage.setItem('token', 'tok123');
    localStorage.setItem('user', '{bad json}');
    renderWithProvider();
    await waitFor(() => {
      expect(screen.getByTestId('is-authenticated').textContent).toBe('false');
    });
  });
});

describe('AuthProvider — login', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('sets user and token after successful login', async () => {
    authAPI.login.mockResolvedValueOnce({
      data: {
        access_token: 'jwt_token',
        user: { id: 1, email: 'admin@test.com', role: 'admin' },
      },
    });

    renderWithProvider();
    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'));

    await act(async () => {
      await userEvent.click(screen.getByText('Login'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('is-authenticated').textContent).toBe('true');
      expect(screen.getByTestId('user-email').textContent).toBe('admin@test.com');
    });
  });

  it('sets isAdmin=true for admin role', async () => {
    authAPI.login.mockResolvedValueOnce({
      data: {
        access_token: 'jwt_token',
        user: { id: 1, email: 'admin@test.com', role: 'admin' },
      },
    });

    renderWithProvider();
    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'));

    await act(async () => {
      await userEvent.click(screen.getByText('Login'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('is-admin').textContent).toBe('true');
    });
  });

  it('saves token to localStorage on login', async () => {
    authAPI.login.mockResolvedValueOnce({
      data: {
        access_token: 'my_saved_token',
        user: { id: 1, email: 'admin@test.com', role: 'admin' },
      },
    });

    renderWithProvider();
    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'));

    await act(async () => {
      await userEvent.click(screen.getByText('Login'));
    });

    await waitFor(() => {
      expect(localStorage.getItem('access_token')).toBe('my_saved_token');
    });
  });

  it('sets error on failed login', async () => {
    authAPI.login.mockRejectedValueOnce({
      response: { data: { detail: 'פרטים שגויים' } },
    });

    renderWithProvider();
    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'));

    await act(async () => {
      await userEvent.click(screen.getByText('Login'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('error').textContent).not.toBe('none');
    });
  });
});

describe('AuthProvider — logout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('clears user and token on logout', async () => {
    authAPI.login.mockResolvedValueOnce({
      data: {
        access_token: 'tok',
        user: { id: 1, email: 'a@test.com', role: 'admin' },
      },
    });

    renderWithProvider();
    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'));

    await act(async () => {
      await userEvent.click(screen.getByText('Login'));
    });
    await waitFor(() => {
      expect(screen.getByTestId('is-authenticated').textContent).toBe('true');
    });

    await act(async () => {
      await userEvent.click(screen.getByText('Logout'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('is-authenticated').textContent).toBe('false');
      expect(screen.getByTestId('user-email').textContent).toBe('none');
    });
  });

  it('removes token from localStorage on logout', async () => {
    localStorage.setItem('token', 'tok');
    localStorage.setItem('access_token', 'tok');
    localStorage.setItem('user', JSON.stringify({ email: 'a@test.com', role: 'admin' }));

    renderWithProvider();
    await waitFor(() => expect(screen.getByTestId('is-authenticated').textContent).toBe('true'));

    await act(async () => {
      await userEvent.click(screen.getByText('Logout'));
    });

    expect(localStorage.getItem('token')).toBeNull();
    expect(localStorage.getItem('access_token')).toBeNull();
  });
});
