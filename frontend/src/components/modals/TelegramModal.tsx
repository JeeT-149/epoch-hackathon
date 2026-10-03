import React from 'react';
import { Language } from '../../types';

interface TelegramModalProps {
  isOpen: boolean;
  onClose: () => void;
  language: Language;
}

export const TelegramModal: React.FC<TelegramModalProps> = ({
  isOpen,
  onClose,
  language,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <div className="bg-surface-container-lowest rounded-3xl p-6 w-full max-w-sm border border-outline-variant shadow-2xl text-center">
        <div className="flex justify-between items-center mb-4">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-2xl">send</span>
            <h3 className="font-bold text-base text-on-surface">
              {language === 'mr' ? 'टेलिग्राम शेतकरी गट' : 'Nashik Farmer Telegram Broadcast'}
            </h3>
          </div>
          <button onClick={onClose} className="p-1 rounded-full hover:bg-surface-container">
            <span className="material-symbols-outlined text-outline">close</span>
          </button>
        </div>

        <p className="text-xs text-on-surface-variant mb-6 leading-relaxed">
          {language === 'mr'
            ? 'थेट बाजार दर, आवक आणि रस्ता स्थितीबाबत शेतकरी मित्रांशी जोडले जा.'
            : 'Join verified regional mandi price broadcast channel for Nashik, Lasalgaon and Pimpalgaon farmers.'}
        </p>

        <a
          href="https://t.me"
          target="_blank"
          rel="noopener noreferrer"
          className="block w-full bg-primary text-on-primary py-3 rounded-xl text-xs font-bold shadow-md hover:opacity-90 mb-3"
        >
          Open Telegram Channel
        </a>

        <button
          onClick={onClose}
          className="w-full bg-surface-container text-on-surface py-2.5 rounded-xl text-xs font-semibold"
        >
          Maybe Later
        </button>
      </div>
    </div>
  );
};
