import React from 'react';
import { Language } from '../../types';

interface LocationModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedLocation: string;
  onSelectLocation: (loc: string) => void;
  language: Language;
}

export const LocationModal: React.FC<LocationModalProps> = ({
  isOpen,
  onClose,
  selectedLocation,
  onSelectLocation,
  language,
}) => {
  if (!isOpen) return null;

  const locations = [
    'Nashik, Maharashtra • Dindori Taluka Block 4B',
    'Nashik, Maharashtra • Niphad Taluka Lasalgaon',
    'Nashik, Maharashtra • Pimpalgaon Baswant',
    'Pune, Maharashtra • Haveli Taluka',
  ];

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <div className="bg-surface-container-lowest rounded-3xl p-6 w-full max-w-sm border border-outline-variant shadow-2xl">
        <div className="flex justify-between items-center mb-4">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-2xl">location_on</span>
            <h3 className="font-bold text-base text-on-surface">
              {language === 'mr' ? 'शेत / मूळ स्थान निवडा' : 'Select Farmgate Origin'}
            </h3>
          </div>
          <button onClick={onClose} className="p-1 rounded-full hover:bg-surface-container">
            <span className="material-symbols-outlined text-outline">close</span>
          </button>
        </div>

        <div className="space-y-2 mb-6">
          {locations.map((loc) => (
            <div
              key={loc}
              onClick={() => {
                onSelectLocation(loc);
                onClose();
              }}
              className={`p-3 rounded-2xl cursor-pointer text-xs font-medium border transition-colors flex items-center justify-between ${
                selectedLocation === loc
                  ? 'bg-primary/10 border-primary text-primary font-bold'
                  : 'bg-surface-container border-outline-variant/30 text-on-surface hover:bg-surface-container-high'
              }`}
            >
              <span>{loc}</span>
              {selectedLocation === loc && (
                <span className="material-symbols-outlined text-base">check</span>
              )}
            </div>
          ))}
        </div>

        <button
          onClick={onClose}
          className="w-full bg-primary text-on-primary py-3 rounded-xl text-xs font-bold shadow-md hover:opacity-90"
        >
          Confirm
        </button>
      </div>
    </div>
  );
};
