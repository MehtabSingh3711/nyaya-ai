'use client';

import React, { useEffect } from 'react';
import { AlertCircle, CheckCircle, Info, X } from 'lucide-react';

export interface ToastMessage {
  id: string;
  type: 'error' | 'success' | 'info';
  message: string;
}

interface ToastProps {
  toast: ToastMessage | null;
  onClose: () => void;
}

export default function Toast({ toast, onClose }: ToastProps) {
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => {
        onClose();
      }, 4000);
      return () => clearTimeout(timer);
    }
  }, [toast, onClose]);

  if (!toast) return null;

  const isError = toast.type === 'error';
  const isSuccess = toast.type === 'success';

  return (
    <div className="fixed bottom-6 right-6 z-50 max-w-sm w-full animate-in slide-in-from-bottom-5 fade-in duration-200">
      <div className={`bg-surface border rounded-xl p-4 shadow-2xl flex items-start gap-3 relative ${
        isError ? 'border-[var(--garnet)]/40' : isSuccess ? 'border-emerald-500/40' : 'border-kite'
      }`}>
        <div className={`p-1.5 rounded-full flex-shrink-0 mt-0.5 ${
          isError ? 'bg-[var(--garnet)]/15 text-[var(--garnet)]' : isSuccess ? 'bg-emerald-500/15 text-emerald-400' : 'bg-[var(--toxic-orange)]/15 text-[var(--toxic-orange)]'
        }`}>
          {isError ? (
            <AlertCircle className="w-4 h-4" />
          ) : isSuccess ? (
            <CheckCircle className="w-4 h-4" />
          ) : (
            <Info className="w-4 h-4" />
          )}
        </div>

        <div className="flex-1 pr-4">
          <h4 className="font-display font-semibold text-xs text-primary capitalize">
            {toast.type === 'error' ? 'Notice' : toast.type}
          </h4>
          <p className="text-xs text-secondary mt-0.5 leading-normal">
            {toast.message}
          </p>
        </div>

        <button
          onClick={onClose}
          className="text-muted hover:text-primary transition-colors p-1 rounded-full hover:bg-[var(--surface-hover)] absolute top-3 right-3"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
