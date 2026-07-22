'use client';

import React from 'react';
import { AlertTriangle, X } from 'lucide-react';

interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  description: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'warning' | 'info';
  onConfirm: () => void;
  onClose: () => void;
}

export default function ConfirmModal({
  isOpen,
  title,
  description,
  confirmText = 'Delete',
  cancelText = 'Cancel',
  variant = 'danger',
  onConfirm,
  onClose,
}: ConfirmModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div className="bg-surface border border-[var(--black-kite-15)] rounded-xl p-6 max-w-md w-full shadow-2xl relative animate-in zoom-in-95 duration-150">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-muted hover:text-primary transition-colors p-1 rounded-full hover:bg-[var(--surface-hover)]"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Header Icon & Title */}
        <div className="flex items-start gap-4 mb-4">
          <div className={`p-3 rounded-full flex-shrink-0 ${
            variant === 'danger' ? 'bg-[var(--garnet)]/15 text-[var(--garnet)]' : 'bg-[var(--toxic-orange)]/15 text-[var(--toxic-orange)]'
          }`}>
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <h3 className="font-display font-bold text-lg text-primary tracking-tight">
              {title}
            </h3>
            <p className="text-xs text-secondary mt-1.5 leading-relaxed">
              {description}
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 mt-6 pt-4 border-t border-[var(--black-kite-15)]">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded text-xs font-medium bg-page border border-[var(--black-kite-15)] text-secondary hover:text-primary hover:bg-[var(--surface-hover)] transition-all"
          >
            {cancelText}
          </button>
          <button
            onClick={() => {
              onConfirm();
              onClose();
            }}
            className={`px-4 py-2 rounded text-xs font-semibold text-white shadow-sm transition-all ${
              variant === 'danger'
                ? 'bg-[var(--garnet)] hover:bg-[#B71C1C]'
                : 'bg-[var(--toxic-orange)] hover:opacity-90'
            }`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
