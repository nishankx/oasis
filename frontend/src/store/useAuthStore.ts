import { create } from 'zustand';
import type { UserRecord } from '../types';
import { api } from '../lib/api';

interface AuthState {
  user: UserRecord | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  initSession: () => Promise<void>;
  setSession: (user: UserRecord, token: string) => void;
  logout: () => Promise<void>;
  loginWithGithub: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('oasis_token'),
  isLoading: true,
  isAuthenticated: false,

  initSession: async () => {
    set({ isLoading: true });
    const token = localStorage.getItem('oasis_token');
    if (!token) {
      set({ user: null, isAuthenticated: false, isLoading: false });
      return;
    }

    try {
      const session = await api.getSession();
      if (session.authenticated && session.user) {
        set({ user: session.user, isAuthenticated: true, isLoading: false });
      } else {
        localStorage.removeItem('oasis_token');
        set({ user: null, token: null, isAuthenticated: false, isLoading: false });
      }
    } catch {
      localStorage.removeItem('oasis_token');
      set({ user: null, token: null, isAuthenticated: false, isLoading: false });
    }
  },

  setSession: (user: UserRecord, token: string) => {
    localStorage.setItem('oasis_token', token);
    localStorage.setItem('oasis_cached_user', JSON.stringify(user));
    set({ user, token, isAuthenticated: true, isLoading: false });
  },

  logout: async () => {
    await api.logout();
    localStorage.removeItem('oasis_cached_user');
    set({ user: null, token: null, isAuthenticated: false, isLoading: false });
  },

  loginWithGithub: async () => {
    const callbackUri = `${window.location.origin}/auth/callback`;
    const { url } = await api.getGitHubAuthUrl(callbackUri);
    window.location.href = url;
  },
}));
