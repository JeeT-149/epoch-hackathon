import React, { useState } from 'react';
import { Language } from '../../types';
import { formatInr } from '../../utils/formatters';

interface HarvestCalculatorModalProps {
  isOpen: boolean;
  onClose: () => void;
  language: Language;
}

export const HarvestCalculatorModal: React.FC<HarvestCalculatorModalProps> = ({
  isOpen,
  onClose,
  language,
}) => {
  const [quantity, setQuantity] = useState('50');
  const [modalPrice, setModalPrice] = useState('2640');
  const [freightRate, setFreightRate] = useState('135');

  if (!isOpen) return null;

  const q = parseFloat(quantity) || 0;
  const price = parseFloat(modalPrice) || 0;
  const freight = parseFloat(freightRate) || 0;

  const gross = q * price;
  const totalFreight = q * freight;
  const netTakeHome = gross - totalFreight;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <div className="bg-surface-container-lowest rounded-3xl p-6 w-full max-w-sm border border-outline-variant shadow-2xl">
        <div className="flex justify-between items-center mb-4">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-2xl">calculate</span>
            <h3 className="font-bold text-base text-on-surface">
              {language === 'mr' ? 'काढणी व परतावा गणक' : 'Harvest Take-Home Calculator'}
            </h3>
          </div>
          <button onClick={onClose} className="p-1 rounded-full hover:bg-surface-container">
            <span className="material-symbols-outlined text-outline">close</span>
          </button>
        </div>

        <div className="space-y-3 mb-5">
          <div>
            <label className="text-xs text-outline font-semibold block mb-1">
              Quantity (Quintals / क्विंटल)
            </label>
            <input
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              className="w-full bg-surface-container border border-outline-variant rounded-xl p-2.5 text-xs text-on-surface font-bold focus:outline-none focus:border-primary"
            />
          </div>

          <div>
            <label className="text-xs text-outline font-semibold block mb-1">
              Mandi Modal Price (₹/quintal)
            </label>
            <input
              type="number"
              value={modalPrice}
              onChange={(e) => setModalPrice(e.target.value)}
              className="w-full bg-surface-container border border-outline-variant rounded-xl p-2.5 text-xs text-on-surface font-bold focus:outline-none focus:border-primary"
            />
          </div>

          <div>
            <label className="text-xs text-outline font-semibold block mb-1">
              Freight & Market Fees (₹/quintal)
            </label>
            <input
              type="number"
              value={freightRate}
              onChange={(e) => setFreightRate(e.target.value)}
              className="w-full bg-surface-container border border-outline-variant rounded-xl p-2.5 text-xs text-on-surface font-bold focus:outline-none focus:border-primary"
            />
          </div>
        </div>

        {/* Calculation Result */}
        <div className="bg-primary/10 border border-primary/30 p-4 rounded-2xl mb-4">
          <span className="text-[11px] text-primary uppercase font-bold tracking-wider block mb-1">
            Total Net Take-Home (निव्वळ परतावा)
          </span>
          <span className="text-2xl font-extrabold text-primary block">
            {formatInr(netTakeHome)}
          </span>
          <span className="text-[11px] text-outline mt-1 block">
            Gross: {formatInr(gross)} • Freight: -{formatInr(totalFreight)}
          </span>
        </div>

        <button
          onClick={onClose}
          className="w-full bg-primary text-on-primary py-3 rounded-xl text-xs font-bold shadow-md hover:opacity-90"
        >
          Done
        </button>
      </div>
    </div>
  );
};
