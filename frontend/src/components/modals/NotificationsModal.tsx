import React from 'react';
import { Language } from '../../types';

interface NotificationsModalProps {
  isOpen: boolean;
  onClose: () => void;
  language: Language;
}

export const NotificationsModal: React.FC<NotificationsModalProps> = ({
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
            <span className="material-symbols-outlined text-primary text-2xl">notifications</span>
            <h3 className="font-bold text-base text-on-surface">
              {language === 'mr' ? 'बाजार सूचना' : 'Market Triggers & Alerts'}
            </h3>
          </div>
          <button onClick={onClose} className="p-1 rounded-full hover:bg-surface-container">
            <span className="material-symbols-outlined text-outline">close</span>
          </button>
        </div>

        <div className="space-y-3 mb-6">
          <div className="p-3 bg-surface-container rounded-2xl border border-outline-variant/30">
            <div className="flex justify-between items-center mb-1">
              <span className="font-bold text-xs text-primary">Price Trigger Alert</span>
              <span className="text-[10px] text-outline">10 mins ago</span>
            </div>
            <p className="text-xs text-on-surface leading-relaxed">
              Lasalgaon modal price hit ₹2,420/q. Your trigger was reached; consider market dispatch today.
            </p>
          </div>

          <div className="p-3 bg-surface-container rounded-2xl border border-outline-variant/30">
            <div className="flex justify-between items-center mb-1">
              <span className="font-bold text-xs text-error">Rain Corridor Risk</span>
              <span className="text-[10px] text-outline">1 hour ago</span>
            </div>
            <p className="text-xs text-on-surface leading-relaxed">
              Heavy unseasonal showers forecast along Dindori-Pimpalgaon road for Day +3.
            </p>
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
