import React from 'react';
import { useTelemetryStore } from '../../store/useTelemetryStore';
import { CheckCircle2, AlertTriangle, Info, XCircle, X } from 'lucide-react';

export const ToastContainer: React.FC = () => {
  const { toasts, removeToast } = useTelemetryStore();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-12 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      {toasts.map((toast) => {
        const icons = {
          success: <CheckCircle2 className="h-4 w-4 text-accent-lime shrink-0" />,
          warning: <AlertTriangle className="h-4 w-4 text-accent-amber shrink-0" />,
          error: <XCircle className="h-4 w-4 text-accent-coral shrink-0" />,
          info: <Info className="h-4 w-4 text-accent-cyan shrink-0" />,
        };

        const borders = {
          success: 'border-accent-lime/40 bg-bg-surface/95 text-text-primary',
          warning: 'border-accent-amber/40 bg-bg-surface/95 text-text-primary',
          error: 'border-accent-coral/40 bg-bg-surface/95 text-text-primary',
          info: 'border-accent-cyan/40 bg-bg-surface/95 text-text-primary',
        };

        return (
          <div
            key={toast.id}
            className={`pointer-events-auto flex items-start gap-3 p-3 rounded border shadow-2xl backdrop-blur-md transition-all font-mono text-xs ${borders[toast.type]}`}
          >
            {icons[toast.type]}
            <div className="flex-1 overflow-hidden">
              <div className="flex items-center justify-between gap-2">
                <span className="font-bold tracking-wider uppercase text-white">{toast.title}</span>
                <span className="text-[10px] text-text-muted">{toast.timestamp}</span>
              </div>
              <p className="mt-1 text-text-secondary text-[11px] leading-relaxed font-sans">{toast.message}</p>
            </div>
            <button
              onClick={() => removeToast(toast.id)}
              className="text-text-muted hover:text-white transition-colors"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
};
