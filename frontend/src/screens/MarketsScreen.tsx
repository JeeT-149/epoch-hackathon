import React, { useState } from 'react';

import { Language, ScreenType, MandiItem } from '../types';



interface MarketsScreenProps {

  language: Language;

  onNavigate: (screen: ScreenType) => void;

  onSelectMandi: (mandi: MandiItem) => void;

}



export const MarketsScreen: React.FC<MarketsScreenProps> = ({

  language,

  onNavigate,

  onSelectMandi,

}) => {

  const [selectedCrop, setSelectedCrop] = useState<'onion' | 'tomato' | 'soybean'>('onion');

  const [searchQuery, setSearchQuery] = useState('');



  const mandisData: MandiItem[] = [

    {

      id: 'lasalgaon',

      rank: 1,

      name: 'Lasalgaon APMC',

      distanceKm: 24,

      location: 'Lasalgaon, Nashik',

      netTakeHome: 1435,

      modalPrice: 1480,

      freightCost: 45,

      arrivalVolume: 18400,

      arrivalTrend: 'Moderate flow',

      arrivalTrendType: 'positive',

      isHighestNet: true,

    },

    {

      id: 'pimpalgaon',

      rank: 2,

      name: 'Pimpalgaon Baswant APMC',

      distanceKm: 14,

      location: 'Nearest Yard, Niphad',

      netTakeHome: 1415,

      modalPrice: 1440,

      freightCost: 25,

      arrivalVolume: 14200,

      arrivalTrend: 'Steady',

      arrivalTrendType: 'steady',

    },

    {

      id: 'nashik-dindori',

      rank: 3,

      name: 'Nashik Dindori Sub-Market',

      distanceKm: 32,

      location: 'Dindori Road, Nashik',

      netTakeHome: 1350,

      modalPrice: 1410,

      freightCost: 60,

      arrivalVolume: 9800,

      arrivalTrend: 'Slow trading',

      arrivalTrendType: 'negative',

    },

    {

      id: 'pune-gultekdi',

      rank: 4,

      name: 'Pune Gultekdi Market Yard',

      distanceKm: 145,

      location: 'Pune APMC',

      netTakeHome: 1520,

      modalPrice: 1680,

      freightCost: 160,

      arrivalVolume: 22000,

      arrivalTrend: 'Heavy rush',

      arrivalTrendType: 'positive',

    },

    {

      id: 'solapur',

      rank: 5,

      name: 'Solapur APMC',

      distanceKm: 260,

      location: 'Solapur Hub',

      netTakeHome: 1310,

      modalPrice: 1580,

      freightCost: 270,

      arrivalVolume: 11500,

      arrivalTrend: 'Steady',

      arrivalTrendType: 'steady',

    },

    {

      id: 'vashi-mumbai',

      rank: 6,

      name: 'Vashi Navi Mumbai APMC',

      distanceKm: 185,

      location: 'Turbhe, Navi Mumbai',

      netTakeHome: 1540,

      modalPrice: 1750,

      freightCost: 210,

      arrivalVolume: 26000,

      arrivalTrend: 'Moderate flow',

      arrivalTrendType: 'positive',

    },

  ];



  const filteredMandis = mandisData.filter((m) =>

    m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||

    m.location.toLowerCase().includes(searchQuery.toLowerCase())

  );



  return (

    <div className="flex flex-col w-full pb-28 pt-16 max-w-xl mx-auto px-margin">

      <div className="pt-2 pb-3">

        <h2 className="text-[22px] font-bold text-on-surface">

          {language === 'mr' ? 'महाराष्ट्र कृषी उत्पन्न बाजार समित्या' : 'Maharashtra APMC Mandis'}

        </h2>

        <p className="text-xs text-on-surface-variant">

          {language === 'mr' ? 'अगमार्कनेट थेट लिलाव दर आणि वाहतूक खर्च वजा जाता निव्वळ नफा' : language === 'hi' ? 'अगमार्कनेट भाव और परिवहन के बाद शुद्ध कमाई' : 'Real-time Agmarknet auctions & net take-home calculation'}

        </p>

      </div>



      {/* Commodity Selector Chips */}

      <div className="flex gap-2 overflow-x-auto pb-2 -mx-margin px-margin no-scrollbar">

        {[

          { id: 'onion', label: language === 'mr' ? 'कांदा' : language === 'hi' ? 'लाल प्याज़' : 'Red Onion' },

          { id: 'tomato', label: language === 'mr' ? 'टोमॅटो' : language === 'hi' ? 'टमाटर' : 'Tomato' },

          { id: 'soybean', label: language === 'mr' ? 'सोयाबीन' : language === 'hi' ? 'सोयाबीन' : 'Soybean' },


        ].map((item) => (

          <button

            key={item.id}

            onClick={() => setSelectedCrop(item.id as any)}

            className={`px-3 py-1.5 rounded-full text-xs font-bold transition-all shrink-0 ${

              selectedCrop === item.id

                ? 'bg-primary text-on-primary shadow-xs'

                : 'bg-surface-container text-on-surface hover:bg-surface-container-high'

            }`}

            type="button"

          >

            {item.label}

          </button>

        ))}

      </div>



      {/* Search Input */}

      <div className="my-2 relative">

        <span className="material-symbols-outlined absolute left-3 top-2.5 text-[20px] text-outline">

          search

        </span>

        <input

          type="text"

          value={searchQuery}

          onChange={(e) => setSearchQuery(e.target.value)}

          placeholder={language === 'mr' ? 'बाजार समिती किंवा शहर शोधा...' : 'Search mandi name or yard...'}

          className="w-full pl-10 pr-4 py-2 rounded-xl bg-surface-container-lowest border border-surface-container-high text-xs sm:text-sm outline-none text-on-surface"

        />

      </div>



      {/* Mandis List */}

      <div className="space-y-3 mt-2">

        {filteredMandis.map((mandi) => (

          <div

            key={mandi.id}

            onClick={() => {

              onSelectMandi(mandi);

              if (selectedCrop === 'onion') {

                onNavigate('mandi-details');

              }

            }}

            className="p-4 rounded-2xl bg-surface-container-lowest border border-surface-container-high/60 shadow-xs hover:border-primary transition-all cursor-pointer"

          >

            <div className="flex items-start justify-between">

              <div>

                <div className="flex items-center gap-2">

                  <h3 className="font-bold text-[15px] text-on-surface">{mandi.name}</h3>

                  {mandi.isHighestNet && (

                    <span className="px-2 py-0.5 rounded-full bg-secondary-container text-on-secondary-container text-[10px] font-bold">

                      ★ Top Net

                    </span>

                  )}

                </div>

                <p className="text-xs text-on-surface-variant flex items-center gap-1 mt-0.5">

                  <span className="material-symbols-outlined text-[14px]">distance</span>

                  <span>{mandi.distanceKm} km • {mandi.location}</span>

                </p>

              </div>



              <div className="text-right">

                <span className="text-[10px] text-outline font-semibold uppercase">Net Rate</span>

                <p className="font-extrabold text-[17px] text-secondary leading-tight">

                  ₹{mandi.netTakeHome}<span className="text-[10px] text-outline font-normal">/q</span>

                </p>

              </div>

            </div>



            <div className="mt-3 grid grid-cols-3 gap-2 bg-surface-container p-2 rounded-xl text-center text-xs">

              <div>

                <span className="text-[10px] text-outline">Modal Rate</span>

                <p className="font-bold text-on-surface">₹{mandi.modalPrice}</p>

              </div>

              <div>

                <span className="text-[10px] text-outline">Freight</span>

                <p className="font-bold text-error">-₹{mandi.freightCost}</p>

              </div>

              <div>

                <span className="text-[10px] text-outline">Daily Arrival</span>

                <p className="font-bold text-primary">{mandi.arrivalVolume.toLocaleString()} qtl</p>

              </div>

            </div>



            <div className="mt-2.5 flex items-center justify-between text-[11px] text-outline pt-1">

              <span>{mandi.arrivalTrend}</span>

              <span className="text-primary font-semibold flex items-center gap-0.5">

                {language === 'mr' ? 'तपशील उघडा' : 'View Mandi'} →

              </span>

            </div>

          </div>

        ))}

      </div>

    </div>

  );

};
