import { create } from 'zustand';

export interface ToastMessage {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: string;
}

interface TelemetryState {
  coords: { x: number; y: number };
  systemStatus: 'ONLINE' | 'STANDBY' | 'EVALUATING';
  agentStatus: 'READY' | 'WORKING' | 'ANALYZING';
  lastSync: number; // seconds ago
  toasts: ToastMessage[];
  setCoords: (x: number, y: number) => void;
  setSystemStatus: (status: 'ONLINE' | 'STANDBY' | 'EVALUATING') => void;
  setAgentStatus: (status: 'READY' | 'WORKING' | 'ANALYZING') => void;
  resetLastSync: () => void;
  addToast: (toast: Omit<ToastMessage, 'id' | 'timestamp'>) => void;
  removeToast: (id: string) => void;
}

export const useTelemetryStore = create<TelemetryState>((set) => ({
  coords: { x: 0, y: 0 },
  systemStatus: 'ONLINE',
  agentStatus: 'READY',
  lastSync: 3,
  toasts: [],

  setCoords: (x: number, y: number) => set({ coords: { x, y } }),
  setSystemStatus: (systemStatus) => set({ systemStatus }),
  setAgentStatus: (agentStatus) => set({ agentStatus }),
  resetLastSync: () => set({ lastSync: 0 }),

  addToast: (toast) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`;
    const newToast: ToastMessage = {
      ...toast,
      id,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
    };

    set((state) => ({ toasts: [...state.toasts, newToast] }));

    // Auto-dismiss after 5s
    setTimeout(() => {
      set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }));
    }, 5000);
  },

  removeToast: (id: string) => {
    set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }));
  },
}));
