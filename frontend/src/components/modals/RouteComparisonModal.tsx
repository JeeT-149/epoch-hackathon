import React from 'react';
import { Language } from '../../types';

interface RouteComparisonModalProps {
  isOpen: boolean;
  onClose: () => void;
  language: Language;
}

export const RouteComparisonModal: React.FC<RouteComparisonModalProps> = ({
  isOpen,
  onClose,
  language,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <div className="bg-surface-container-lowest rounded-3xl p-6 w-full max-w-sm border border-outline-variant shadow-2xl">
        <div className="flex justify-between items-center mb-4">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-2xl">alt_route</span>
            <h3 className="font-bold text-base text-on-surface">
              {language === 'mr' ? 'वाहतूक मार्ग तुलना' : 'Transport Corridor Comparison'}
            </h3>
          </div>
          <button onClick={onClose} className="p-1 rounded-full hover:bg-surface-container">
            <span className="material-symbols-outlined text-outline">close</span>
          </button>
        </div>

        <div className="space-y-3 mb-5">
          <div className="p-3 bg-primary/10 rounded-2xl border border-primary/30">
            <div className="flex justify-between items-center mb-1">
              <span className="font-bold text-xs text-primary">Route 1: To Pimpalgaon APMC</span>
              <span className="text-xs font-extrabold text-primary">42 mins</span>
            </div>
            <p className="text-[11px] text-on-surface-variant">26 km via NH 848 • Clear road conditions</p>
            <p className="text-[11px] text-outline font-medium mt-1">Freight: ₹135/quintal</p>
          </div>

          <div className="p-3 bg-surface-container rounded-2xl border border-outline-variant/30">
            <div className="flex justify-between items-center mb-1">
              <span className="font-bold text-xs text-on-surface">Route 2: To Lasalgaon APMC</span>
              <span className="text-xs font-bold text-on-surface">58 mins</span>
            </div>
            <p className="text-[11px] text-on-surface-variant">32 km via Niphad road • Moderate tractor queues</p>
            <p className="text-[11px] text-outline font-medium mt-1">Freight: ₹160/quintal</p>
          </div>
        </div>

        <button
          onClick={onClose}
          className="w-full bg-primary text-on-primary py-3 rounded-xl text-xs font-bold shadow-md hover:opacity-90"
        >
          Close
        </button>
      </div>
    </div>
  );
};
