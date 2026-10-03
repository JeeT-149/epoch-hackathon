import React, { useState } from 'react';

import { Language, ScreenType } from '../types';

import { CROPS_AFFECTED } from '../data/mockData';
import { api } from '../api/adapter';
import { RegretReceipt } from '../contracts/schemas';



interface MyCropsScreenProps {

  language: Language;

  onNavigate: (screen: ScreenType) => void;

  onOpenHarvestCalculator: () => void;

}



export const MyCropsScreen: React.FC<MyCropsScreenProps> = ({

  language,

  onNavigate,

  onOpenHarvestCalculator,

}) => {

  const [selectedCropId, setSelectedCropId] = useState<string>('onion-alert');
  const [actualPrice, setActualPrice] = useState('');
  const [saleMandi, setSaleMandi] = useState('Lasalgaon Mandi');
  const [saleDate, setSaleDate] = useState('2026-10-03');
  const [receipt, setReceipt] = useState<RegretReceipt | null>(null);
  const [outcomeLoading, setOutcomeLoading] = useState(false);



  const plotDetails = [

    {

      id: 'onion-alert',

      acreage: '4.5 Acres',

      sowingDate: 'Nov 12',

      expectedYield: '85 Quintals',

      readiness: '92% - Curing in shade',

      soilMoisture: '68% (Saturated)',

      action: 'Hold dispatch for 3-5 days',

    },

    {

      id: 'tomato-alert',

      acreage: '3.0 Acres',

      sowingDate: 'Dec 05',

      expectedYield: '40 Quintals',

      readiness: '80% - Peak fruiting',

      soilMoisture: '62% (Moist)',

      action: 'Spray bio-fungicide today',

    },

    {

      id: 'soybean-alert',

      acreage: '6.0 Acres',

      sowingDate: 'Jul 20',

      expectedYield: '75 Quintals',

      readiness: '65% - Pod filling',

      soilMoisture: '54% (Favorable)',

      action: 'Monitor seed enlargement',

    },

  ];



  return (

    <div className="flex flex-col w-full pb-28 pt-16 max-w-xl mx-auto px-margin">

      <div className="pt-2 pb-4 flex items-center justify-between">

        <div>

          <h2 className="text-[22px] font-bold text-on-surface">

            {language === 'mr' ? 'माझी पिके आणि शेतजमीन' : language === 'hi' ? 'मेरी फसल और खेत' : 'My Monitored Crops'}

          </h2>

          <p className="text-xs text-on-surface-variant">

            {language === 'mr' ? 'दिंडोरी तालुका • एकूण १८ एकर' : language === 'hi' ? 'दिंडोरी तालुका • कुल 18 एकड़' : 'Dindori Taluka • 18 Total Acres'}

          </p>

        </div>



        <button

          onClick={onOpenHarvestCalculator}

          className="px-3 py-1.5 rounded-full bg-secondary-container text-on-secondary-container text-xs font-bold flex items-center gap-1 hover:bg-secondary-container/80 transition-all active:scale-95"

          type="button"

        >

          <span className="material-symbols-outlined text-[16px]">calculate</span>

          <span>{language === 'mr' ? 'नफा मोजा' : language === 'hi' ? 'फसल दर्ज करें' : 'Log Harvest'}</span>

        </button>

      </div>



      {/* Crops List */}

      <div className="space-y-4">

        {CROPS_AFFECTED.map((crop: any) => {

          const detail = plotDetails.find((p) => p.id === crop.id);

          const isSelected = selectedCropId === crop.id;



          return (

            <div

              key={crop.id}

              onClick={() => setSelectedCropId(crop.id)}

              className={`p-4 rounded-2xl bg-surface-container-lowest border transition-all cursor-pointer shadow-sm ${

                isSelected

                  ? 'border-primary ring-2 ring-primary/20'

                  : 'border-surface-container-high/60 hover:border-primary/40'

              }`}

            >

              <div className="flex items-start justify-between gap-3">

                <div className="flex items-center gap-3">

                  <img

                    src={crop.imageUrl}

                    alt={crop.name.en}

                    className="w-14 h-14 rounded-xl object-cover shadow-xs"

                  />

                  <div>

                    <h3 className="font-bold text-[16px] text-on-surface">

                      {crop.name[language]}

                    </h3>

                    <p className="text-xs text-on-surface-variant">

                      {crop.plot} • {detail?.acreage}

                    </p>

                    <span className="text-[11px] font-semibold text-primary">

                      {crop.stage[language]}

                    </span>

                  </div>

                </div>



                <span

                  className={`px-2.5 py-1 rounded-full text-[11px] font-bold shrink-0 ${

                    crop.statusType === 'urgent'

                      ? 'bg-error/15 text-error'

                      : crop.statusType === 'alert'

                      ? 'bg-[#EEE0D1] text-[#4E453A]'

                      : crop.statusType === 'favorable'

                      ? 'bg-secondary-container text-on-secondary-container'

                      : 'bg-surface-variant text-on-surface-variant'

                  }`}

                >

                  {crop.statusTag[language]}

                </span>

              </div>



              {/* Agronomic status grid */}

              <div className="grid grid-cols-3 gap-2 bg-surface-container p-2.5 rounded-xl text-center mt-3 text-xs">

                <div>

                  <span className="text-[10px] text-outline uppercase font-semibold">

                    {language === 'mr' ? 'अपेक्षित उत्पादन' : 'Est. Yield'}

                  </span>

                  <p className="font-bold text-on-surface mt-0.5">{detail?.expectedYield}</p>

                </div>

                <div className="border-x border-outline-variant/40">

                  <span className="text-[10px] text-outline uppercase font-semibold">

                    {language === 'mr' ? 'माती ओलावा' : 'Soil Moisture'}

                  </span>

                  <p className="font-bold text-secondary mt-0.5">{detail?.soilMoisture}</p>

                </div>

                <div>

                  <span className="text-[10px] text-outline uppercase font-semibold">

                    {language === 'mr' ? 'काढणी स्थिती' : 'Readiness'}

                  </span>

                  <p className="font-bold text-primary mt-0.5">{detail?.readiness}</p>

                </div>

              </div>



              <div className="mt-3 flex items-center justify-between pt-2 border-t border-surface-container-high/40 text-xs">

                <span className="text-on-surface-variant font-medium">

                  {language === 'mr' ? 'शिफारस: ' : 'Recommendation: '}

                  <strong className="text-on-surface">{detail?.action}</strong>

                </span>



                <button

                  onClick={(e) => {

                    e.stopPropagation();

                    if (crop.id === 'onion-alert') {

                      onNavigate('mandi-details');

                    } else {

                      onNavigate('weather');

                    }

                  }}

                  className="text-primary font-bold flex items-center gap-1 hover:underline"

                  type="button"

                >

                  <span>{language === 'mr' ? 'तपशील' : 'Details'}</span>

                  <span className="material-symbols-outlined text-[14px]">arrow_forward</span>

                </button>

              </div>

            </div>

          );

        })}

      </div>

      <section className="mt-6 p-4 rounded-2xl bg-surface-container-lowest border border-surface-container-high/70">
        <div className="flex items-center gap-2"><span className="material-symbols-outlined text-[18px] text-primary">receipt_long</span><div><h3 className="font-bold text-[15px]">What price did you get?</h3><p className="text-[11px] text-on-surface-variant">Capture the outcome of an existing plan.</p></div></div>
        <form className="mt-4 space-y-2" onSubmit={async (event) => { event.preventDefault(); if (!actualPrice) return; setOutcomeLoading(true); try { const next = await api.recordOutcome({ session_id: 'mock-session-wait', crop: 'Onion', mandi_id: saleMandi === 'Pimpalgaon Baswant' ? 'mh_nashik_pimpalgaon' : saleMandi === 'Nashik APMC' ? 'mh_nashik_local' : 'mh_nashik_lasalgaon', actual_price: Number(actualPrice), quantity_q: 50, sale_date: saleDate }); setReceipt(next); } finally { setOutcomeLoading(false); } }}>
          <div className="grid grid-cols-2 gap-2"><input required type="number" value={actualPrice} onChange={(event) => setActualPrice(event.target.value)} placeholder="Price / q" className="rounded-xl bg-surface-container px-3 py-2 text-xs outline-none" /><input required type="date" value={saleDate} onChange={(event) => setSaleDate(event.target.value)} className="rounded-xl bg-surface-container px-3 py-2 text-xs outline-none" /></div>
          <select value={saleMandi} onChange={(event) => setSaleMandi(event.target.value)} className="w-full rounded-xl bg-surface-container px-3 py-2 text-xs outline-none"><option>Lasalgaon Mandi</option><option>Pimpalgaon Baswant</option><option>Nashik APMC</option></select>
          <button disabled={outcomeLoading || !actualPrice} className="w-full rounded-xl bg-primary text-on-primary py-2.5 text-xs font-bold disabled:opacity-50" type="submit">{outcomeLoading ? 'Saving outcome…' : 'Save outcome'}</button>
        </form>
        {receipt && <div className="mt-4 p-3 rounded-xl bg-secondary-container/60"><div className="flex justify-between items-start"><div><p className="text-[10px] uppercase font-bold text-on-secondary-container">Regret receipt</p><p className="text-2xl font-bold mt-1">{receipt.regret_per_q >= 0 ? '+' : ''}₹{receipt.regret_per_q.toLocaleString('en-IN')} / q</p></div>{receipt.is_simulated && <span className="px-2 py-1 rounded-full bg-tertiary text-on-tertiary text-[10px] font-bold">SIMULATED</span>}</div><div className="grid grid-cols-2 gap-2 mt-3 text-xs"><p>Actual net <strong className="block">₹{receipt.actual_net_return.toLocaleString('en-IN')}</strong></p><p>Counterfactual <strong className="block">₹{receipt.counterfactual_net_return.toLocaleString('en-IN')}</strong></p></div><p className="text-[10px] text-on-surface-variant mt-3">{receipt.note}</p></div>}
        {receipt && <div className="mt-3 pt-3 border-t border-surface-container-high/60"><p className="text-[10px] uppercase font-bold text-outline">Recent outcomes</p><div className="flex items-center justify-between mt-2 text-xs"><span>{receipt.sell_date} · {receipt.mandi_id.replace(/_/g, ' ')}</span><strong className={receipt.regret_per_q >= 0 ? 'text-secondary' : 'text-error'}>{receipt.regret_per_q >= 0 ? '+' : ''}₹{receipt.regret_per_q.toLocaleString('en-IN')} / q</strong></div></div>}
      </section>

    </div>

  );

};
