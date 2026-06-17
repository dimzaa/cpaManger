import { create } from 'zustand';
import { authAPI } from './api';

export const useAuthStore = create((set, get) => ({
  user: null,
  token: localStorage.getItem('access_token') || null,
  loading: false,
  error: null,

  login: async (email, password) => {
    set({ loading: true, error: null });
    try {
      const response = await authAPI.login(email, password);
      const { access_token, user } = response.data;

      localStorage.setItem('access_token', access_token);
      set({
        token: access_token,
        user,
        loading: false,
      });

      return true;
    } catch (error) {
      const message = error.response?.data?.detail || 'Login failed';
      set({
        error: message,
        loading: false,
      });
      return false;
    }
  },

  register: async (userData) => {
    set({ loading: true, error: null });
    try {
      const response = await authAPI.register(userData);
      const { access_token, user } = response.data;

      localStorage.setItem('access_token', access_token);
      set({
        token: access_token,
        user,
        loading: false,
      });

      return true;
    } catch (error) {
      const message = error.response?.data?.detail || 'Registration failed';
      set({
        error: message,
        loading: false,
      });
      return false;
    }
  },

  logout: () => {
    localStorage.removeItem('access_token');
    set({
      token: null,
      user: null,
      error: null,
    });
  },

  isAuthenticated: () => get().token !== null,
  isAdmin: () => get().user?.role === 'admin',
  getMunicipalityId: () => get().user?.municipality_id,
}));
