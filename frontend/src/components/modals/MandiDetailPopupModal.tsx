import React from 'react';
import { Language, MandiItem } from '../../types';
import { formatInr } from '../../utils/formatters';

interface MandiDetailPopupModalProps {
  mandi: MandiItem | null;
  onClose: () => void;
  language: Language;
  onOpenHarvestCalculator: () => void;
}

export const MandiDetailPopupModal: React.FC<MandiDetailPopupModalProps> = ({
  mandi,
  onClose,
  language,
  onOpenHarvestCalculator,
}) => {
  if (!mandi) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <div className="bg-surface-container-lowest rounded-3xl p-6 w-full max-w-sm border border-outline-variant shadow-2xl">
        <div className="flex justify-between items-start mb-4">
          <div>
            <span className="text-[10px] font-bold text-primary uppercase tracking-wider block">
              Mandi Profile #{mandi.rank}
            </span>
            <h3 className="font-bold text-base text-on-surface mt-0.5">{mandi.name}</h3>
            <p className="text-xs text-on-surface-variant">{mandi.location} • {mandi.distanceKm} km</p>
          </div>
          <button onClick={onClose} className="p-1 rounded-full hover:bg-surface-container">
            <span className="material-symbols-outlined text-outline">close</span>
          </button>
        </div>

        <div className="bg-surface-container p-4 rounded-2xl border border-outline-variant/30 mb-4">
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs text-outline">Net Realisation:</span>
            <span className="text-lg font-extrabold text-primary">{formatInr(mandi.netTakeHome)}/q</span>
          </div>
          <div className="flex justify-between items-center text-xs text-on-surface-variant mb-1">
            <span>Modal Reference Price:</span>
            <span>{formatInr(mandi.modalPrice)}/q</span>
          </div>
          <div className="flex justify-between items-center text-xs text-on-surface-variant">
            <span>Estimated Freight:</span>
            <span>-{formatInr(mandi.freightCost)}/q</span>
          </div>
        </div>

        <div className="mb-5 text-xs text-outline leading-relaxed italic">
          ℹ️ Modal price is a market-level reference, not a guaranteed realisation price.
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => {
              onClose();
              onOpenHarvestCalculator();
            }}
            className="flex-1 bg-primary text-on-primary py-3 rounded-xl text-xs font-bold shadow-md hover:opacity-90"
          >
            Calculate Return
          </button>
          <button
            onClick={onClose}
            className="bg-surface-container text-on-surface px-4 py-3 rounded-xl text-xs font-bold"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
