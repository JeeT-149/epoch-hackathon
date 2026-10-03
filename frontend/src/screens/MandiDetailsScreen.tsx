import React, { useState } from 'react';

import { Language, MandiItem } from '../types';

import { ASSETS, BEST_MANDIS } from '../data/mockData';



interface MandiDetailsScreenProps {

  language: Language;

  onOpenHarvestCalculator: () => void;

  onOpenMandiModal: (mandi: MandiItem) => void;

  onOpenTelegramModal: () => void;

  onNavigateHome: () => void;

}



export const MandiDetailsScreen: React.FC<MandiDetailsScreenProps> = ({

  language,

  onOpenHarvestCalculator,

  onOpenMandiModal,

  onOpenTelegramModal,

}) => {

  const [selectedMandiId, setSelectedMandiId] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<'all' | 'nearest' | 'highest-net'>('all');

  const [hoveredPoint, setHoveredPoint] = useState<string | null>(null);



  const displayedMandis = BEST_MANDIS.filter((m: any) => {

    if (activeTab === 'nearest') return m.distanceKm <= 20;

    if (activeTab === 'highest-net') return m.netTakeHome >= 1420;

    return true;

  });



  return (

    <div className="flex-1 flex flex-col relative w-full pt-16 pb-28 bg-surface px-margin max-w-xl mx-auto">

      <div className="flex flex-col w-full pb-6">

        

        {/* Top Hero Produce Showcase */}

        <div className="relative w-full h-[210px] rounded-2xl overflow-hidden shadow-md bg-surface-container mt-2">

          <img

            src={ASSETS.onionSacksHero}

            alt="Fresh red onions in burlap sacks"

            className="w-full h-full object-cover object-center"

          />

          <div className="absolute inset-0 bg-gradient-to-t from-on-background/90 via-on-background/40 to-transparent"></div>



          <div className="absolute bottom-0 left-0 right-0 p-4 flex flex-col justify-end text-on-primary">

            <div className="flex items-center gap-space-xs mb-1">

              <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-secondary-fixed text-on-secondary-fixed text-xs font-semibold">

                {language === 'mr' ? 'नाशिक हब' : 'Nashik Hub'}

              </span>

              <span className="text-xs text-surface-container-high opacity-90 font-medium">

                {language === 'mr' ? 'गावराण / रब्बी दर्जा' : 'Garva / Rabi Quality'}

              </span>

            </div>



            <div className="flex items-end justify-between gap-2">

              <div className="min-w-0">

                <h2 className="text-[24px] font-extrabold tracking-tight text-on-primary truncate">

                  {language === 'mr' ? 'लाल कांदा (Nashik Lal)' : 'Red Onion (लाल कांदा)'}

                </h2>

                <p className="text-[17px] text-primary-fixed font-bold mt-0.5">

                  ₹1,420{' '}

                  <span className="text-xs text-inverse-on-surface opacity-80 font-normal">

                    {language === 'mr' ? '/ क्विंटल (सरासरी भाव)' : '/ quintal (Modal)'}

                  </span>

                </p>

              </div>



              <div className="shrink-0 flex items-center gap-1 bg-surface-container-lowest px-2.5 py-1.5 rounded-full shadow-sm text-secondary">

                <span className="material-symbols-outlined text-[16px] font-bold">arrow_upward</span>

                <span className="text-xs font-bold">+4.8%</span>

                <span className="text-[10px] text-outline hidden xs:inline">(₹65/qtl)</span>

              </div>

            </div>

          </div>

        </div>



        {/* AI Harvest Advisory Banner */}

        <div className="mt-4 p-4 rounded-2xl bg-secondary-container/40 shadow-sm relative overflow-hidden border border-secondary/20">

          <div className="flex items-start gap-3">

            <div className="w-10 h-10 rounded-full bg-secondary text-on-secondary flex items-center justify-center shrink-0 shadow-sm mt-0.5">

              <span className="material-symbols-outlined text-[22px]">psychology_alt</span>

            </div>

            <div className="flex-1 min-w-0">

              <div className="flex items-center justify-between gap-2">

                <span className="text-xs font-bold text-on-secondary-container tracking-wide uppercase">

                  {language === 'mr' ? 'सल्ला: ५–७ दिवस थांबा' : 'Advisory: Wait 5–7 Days'}

                </span>

                <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary text-[11px] font-semibold">

                  {language === 'mr' ? 'उच्च विश्वासार्हता' : 'High Confidence'}

                </span>

              </div>

              <p className="text-[13px] text-on-surface mt-1 leading-snug">

                {language === 'mr'

                  ? 'लासलगाव आणि पिंपळगाव बाजारात आवक कमी होण्याची शक्यता. अपेक्षित फायदा: '

                  : 'Expected arrival slowdown in Lasalgaon & Pimpalgaon. Typical outcome: '}

                <span className="font-bold text-secondary">+₹180/qtl</span>{' '}

                <span className="text-on-surface-variant text-xs">

                  {language === 'mr' ? '(संभाव्य कक्षा: +₹६० ते +₹२९०)' : '(Likely range: +₹60 to +₹290)'}

                </span>.

              </p>

            </div>

          </div>

        </div>



        {/* 14-Day Price Trend & Forecast (Interactive Graphic) */}

        <div className="mt-4 rounded-2xl bg-surface-container-lowest p-4 shadow-sm border border-surface-container-high/40">

          <div className="flex items-start justify-between">

            <div>

              <h3 className="text-[17px] font-bold text-on-surface">

                {language === 'mr' ? '१४-दिवसीय भाव कल आणि अंदाज' : '14-Day Price Trend & Forecast'}

              </h3>

              <p className="text-[11px] text-on-surface-variant mt-0.5">

                {language === 'mr'

                  ? 'मागील ७ दिवसांचे प्रत्यक्ष भाव + पुढील ७ दिवसांचे अंदाज क्षेत्र'

                  : 'Past 7 days modal price + 7 days forecast envelope'}

              </p>

            </div>

            <span className="material-symbols-outlined text-outline text-[22px]">show_chart</span>

          </div>



          {/* Interactive Chart Canvas SVG */}

          <div className="mt-3 relative w-full overflow-hidden">

            <svg

              className="w-full h-44 overflow-visible cursor-crosshair"

              preserveAspectRatio="none"

              viewBox="0 0 350 170"

            >

              <defs>

                {/* Shaded range fill */}

                <linearGradient id="rangeBand" x1="0" x2="0" y1="0" y2="1">

                  <stop offset="0%" stopColor="#baccb4" stopOpacity="0.55" />

                  <stop offset="100%" stopColor="#baccb4" stopOpacity="0.1" />

                </linearGradient>

                {/* Grid styling */}

                <pattern id="gridLines" patternUnits="userSpaceOnUse" width="350" height="35">

                  <line x1="36" x2="350" y1="35" y2="35" stroke="#d9e6d5" strokeWidth="1" strokeDasharray="3,3" />

                </pattern>

              </defs>



              {/* Background horizontal guidelines */}

              <rect x="36" y="10" width="314" height="120" fill="url(#gridLines)" />



              {/* Y-Axis Labels */}

              <text x="30" y="24" fill="#747871" fontSize="10" fontWeight="500" textAnchor="end">₹1,750</text>

              <text x="30" y="60" fill="#747871" fontSize="10" fontWeight="500" textAnchor="end">₹1,600</text>

              <text x="30" y="95" fill="#747871" fontSize="10" fontWeight="500" textAnchor="end">₹1,450</text>

              <text x="30" y="130" fill="#747871" fontSize="10" fontWeight="500" textAnchor="end">₹1,300</text>



              {/* Divider line representing 'Today' */}

              <line x1="175" x2="175" y1="12" y2="135" stroke="#c4c8bf" strokeWidth="1.5" strokeDasharray="2,2" />

              <rect x="156" y="6" width="38" height="14" rx="7" fill="#dfecdb" />

              <text x="175" y="16.5" fill="#3b4b39" fontSize="9" fontWeight="bold" textAnchor="middle">TODAY</text>



              {/* Target Trigger Line (₹1,650) */}

              <line x1="36" x2="346" y1="48" y2="48" stroke="#ba1a1a" strokeWidth="1.2" strokeDasharray="4,4" opacity="0.75" />

              <text x="344" y="44" fill="#ba1a1a" fontSize="9" fontWeight="600" textAnchor="end">

                {language === 'mr' ? 'विक्री लक्ष्य ₹१,६५०' : 'Sell Target ₹1,650'}

              </text>



              {/* Forecast Area Band (Day 0 to +7) */}

              <polygon

                points="175,102 210,85 250,68 295,45 345,34 345,98 295,106 250,112 210,116 175,102"

                fill="url(#rangeBand)"

              />



              {/* Forecast Upper & Lower Bounds */}

              <path d="M 175 102 Q 250 56 345 34" fill="none" stroke="#687965" strokeWidth="1" strokeDasharray="2,2" />

              <path d="M 175 102 Q 250 110 345 98" fill="none" stroke="#687965" strokeWidth="1" strokeDasharray="2,2" />



              {/* Historical Trajectory (Past 7 Days to Today) */}

              <path

                d="M 40 126 L 62 120 L 85 124 L 108 114 L 130 110 L 152 106 L 175 102"

                fill="none"

                stroke="#50604d"

                strokeWidth="3"

                strokeLinecap="round"

                strokeLinejoin="round"

              />



              {/* Forecast Median Expected Line */}

              <path

                d="M 175 102 L 210 92 L 250 82 L 295 64 L 345 52"

                fill="none"

                stroke="#4c6546"

                strokeWidth="2.5"

                strokeDasharray="4,4"

                strokeLinecap="round"

              />



              {/* Historical Dots */}

              <circle cx="40" cy="126" r="3" fill="#50604d" />

              <circle cx="85" cy="124" r="3" fill="#50604d" />

              <circle cx="130" cy="110" r="3" fill="#50604d" />



              {/* Today Node with Badge */}

              <circle

                cx="175"

                cy="102"

                r="5"

                fill="#f0fdec"

                stroke="#50604d"

                strokeWidth="3"

                className="cursor-pointer"

                onMouseEnter={() => setHoveredPoint('today')}

              />

              <rect x="140" y="112" width="70" height="18" rx="6" fill="#50604d" />

              <text x="175" y="124" fill="#ffffff" fontSize="10" fontWeight="bold" textAnchor="middle">₹1,420</text>



              {/* Day +5 Highlight Node */}

              <circle

                cx="295"

                cy="64"

                r="4.5"

                fill="#f0fdec"

                stroke="#4c6546"

                strokeWidth="2.5"

                className="cursor-pointer"

                onMouseEnter={() => setHoveredPoint('day5')}

              />

              <rect x="264" y="24" width="62" height="18" rx="6" fill="#ceebc4" />

              <text x="295" y="36.5" fill="#0a2008" fontSize="9.5" fontWeight="bold" textAnchor="middle">+5d: ₹1,600</text>



              {/* X-Axis Timeline Dates */}

              <text x="40" y="152" fill="#747871" fontSize="9.5" textAnchor="middle">7d ago</text>

              <text x="108" y="152" fill="#747871" fontSize="9.5" textAnchor="middle">3d ago</text>

              <text x="175" y="152" fill="#131e14" fontSize="9.5" fontWeight="bold" textAnchor="middle">Today</text>

              <text x="250" y="152" fill="#747871" fontSize="9.5" textAnchor="middle">+3 Days</text>

              <text x="330" y="152" fill="#747871" fontSize="9.5" textAnchor="middle">+7 Days</text>

            </svg>

          </div>



          {/* Interactive Forecast Explanation */}

          {hoveredPoint && (

            <div className="mt-2 text-xs bg-surface-container p-2 rounded-lg text-on-surface-variant flex items-center justify-between">

              <span>

                {hoveredPoint === 'today'

                  ? (language === 'mr' ? 'आजचा दर: ₹१,४२० • आवक स्थिर' : "Today: ₹1,420 • Steady Arrival")

                  : (language === 'mr' ? '५ दिवसांनंतर: ₹१,६०० • नफा +₹१८०/क्विं' : "In 5 Days: ₹1,600 • Expected gain +₹180/qtl")}

              </span>

              <button

                onClick={onOpenHarvestCalculator}

                className="text-primary font-bold hover:underline"

              >

                {language === 'mr' ? 'नफा मोजा' : 'Calculate Profit'}

              </button>

            </div>

          )}



          {/* Chart Legend Matrix */}

          <div className="mt-2 pt-3 bg-surface-container-low rounded-xl px-3 py-2 flex flex-wrap items-center justify-between gap-2 text-xs text-on-surface-variant">

            <div className="flex items-center gap-1.5">

              <span className="w-3.5 h-1 bg-primary rounded-full inline-block"></span>

              <span>{language === 'mr' ? 'प्रत्यक्ष' : 'Actual'}</span>

            </div>

            <div className="flex items-center gap-1.5">

              <span className="w-3.5 h-2 bg-primary-fixed-dim rounded inline-block"></span>

              <span>{language === 'mr' ? 'संभाव्य कक्षा' : 'Likely Range'}</span>

            </div>

            <div className="flex items-center gap-1.5">

              <span className="w-3.5 h-0.5 border-b-2 border-dashed border-secondary inline-block"></span>

              <span>{language === 'mr' ? 'अंदाजित' : 'Predicted'}</span>

            </div>

            <div className="flex items-center gap-1.5">

              <span className="w-2.5 h-0.5 border-b border-error inline-block"></span>

              <span className="text-error">{language === 'mr' ? 'लक्ष्य ₹१,६५०' : 'Target ₹1,650'}</span>

            </div>

          </div>

        </div>



        {/* Best Mandis Ranking Section */}

        <div className="mt-6 flex flex-col gap-space-sm">

          <div className="flex items-center justify-between">

            <div>

              <h3 className="text-[17px] font-bold text-on-surface">

                {language === 'mr' ? 'आजचे सर्वोत्तम बाजार' : language === 'hi' ? 'आज की सबसे अच्छी मंडियां' : 'Best Mandis Today'}

              </h3>

              <p className="text-[11px] text-on-surface-variant">

                {language === 'mr'

                  ? 'वाहतूक खर्च वजा जाता सर्वाधिक निव्वळ नफ्यानुसार क्रमवारी'

                  : 'Ranked by highest net return after transport cost'}

              </p>

            </div>



            {/* Filter Pills */}

            <div className="flex items-center gap-1">

              <button

                onClick={() => setActiveTab(activeTab === 'all' ? 'nearest' : 'all')}

                className="px-2.5 py-1 rounded-full bg-surface-container-high text-on-surface-variant text-xs font-semibold flex items-center gap-1 hover:bg-surface-container-highest transition-colors"

                type="button"

              >

                <span className="material-symbols-outlined text-[15px]">tune</span>

                <span>{activeTab === 'all' ? 'Filters' : 'Nearest'}</span>

              </button>

            </div>

          </div>



          {/* Mandi Cards List */}

          {displayedMandis.map((mandi: any) => {

            const isSelected = selectedMandiId === mandi.id;



            return (

              <div

                key={mandi.id}

                onClick={() => {

                  setSelectedMandiId(mandi.id);

                  onOpenMandiModal(mandi);

                }}

                className={`rounded-2xl bg-surface-container-lowest p-4 shadow-sm relative overflow-hidden border transition-all cursor-pointer ${

                  isSelected ? 'border-primary ring-2 ring-primary/20' : 'border-surface-container-high/40 hover:border-primary/40'

                }`}

              >

                {/* Highest Net Banner */}

                {mandi.isHighestNet && (

                  <div className="absolute top-0 right-0 bg-secondary-container px-3 py-1 rounded-bl-xl shadow-xs">

                    <span className="text-[11px] font-bold text-on-secondary-container flex items-center gap-1">

                      <span className="material-symbols-outlined text-[13px]">star</span>

                      <span>{language === 'mr' ? 'सर्वाधिक नफा' : 'Highest Net'}</span>

                    </span>

                  </div>

                )}



                <div className="flex items-start gap-3">

                  <div

                    className={`w-11 h-11 rounded-xl flex items-center justify-center font-bold text-lg shrink-0 ${

                      mandi.isHighestNet

                        ? 'bg-surface-container-high text-primary'

                        : 'bg-surface-container text-on-surface-variant'

                    }`}

                  >

                    {mandi.rank}

                  </div>



                  <div className="flex-1 min-w-0 pr-14">

                    <h4 className="text-[16px] font-bold text-on-surface truncate">

                      {mandi.name}

                    </h4>

                    <p className="text-xs text-on-surface-variant flex items-center gap-1 mt-0.5">

                      <span className="material-symbols-outlined text-[14px]">distance</span>

                      <span>{mandi.distanceKm} km away • {mandi.location}</span>

                    </p>

                  </div>

                </div>



                {/* Data breakdown box */}

                <div className="mt-3.5 p-3 rounded-xl bg-surface-container-low flex items-center justify-between">

                  <div>

                    <span className="text-[11px] font-medium text-outline">

                      {language === 'mr' ? 'हाती येणारा निव्वळ दर' : 'Net Take-Home'}

                    </span>

                    <p className="text-[20px] text-secondary font-extrabold leading-tight">

                      ₹{mandi.netTakeHome.toLocaleString()}{' '}

                      <span className="text-xs font-normal text-on-surface-variant">/ qtl</span>

                    </p>

                  </div>



                  <div className="text-right">

                    <div className="text-xs text-on-surface-variant">

                      {language === 'mr' ? 'मोडल भाव:' : 'Modal:'}{' '}

                      <span className="font-semibold text-on-surface">₹{mandi.modalPrice.toLocaleString()}</span>

                    </div>

                    <div className="text-xs text-error font-medium mt-0.5">

                      {language === 'mr' ? 'वाहतूक खर्च:' : 'Freight:'} -₹{mandi.freightCost}/qtl

                    </div>

                  </div>

                </div>



                <div className="mt-3 flex items-center justify-between text-xs text-on-surface-variant pt-2 border-t border-surface-container-high/30">

                  <div className="flex items-center gap-1">

                    <span

                      className={`w-2 h-2 rounded-full ${

                        mandi.arrivalTrendType === 'positive'

                          ? 'bg-secondary'

                          : mandi.arrivalTrendType === 'steady'

                          ? 'bg-outline'

                          : 'bg-error'

                      }`}

                    ></span>

                    <span>

                      {language === 'mr' ? 'आवक:' : 'Arrival:'}{' '}

                      {mandi.arrivalVolume.toLocaleString()} qtl ({mandi.arrivalTrend})

                    </span>

                  </div>



                  <span className="text-primary font-semibold flex items-center gap-0.5">

                    {language === 'mr' ? 'तपशील पहा' : 'View details'}{' '}

                    <span className="material-symbols-outlined text-[14px]">chevron_right</span>

                  </span>

                </div>

              </div>

            );

          })}

        </div>



        {/* Transparent Regulatory & Methodology Footnote */}

        <div className="mt-4 px-3 py-3 rounded-xl bg-surface-container/60 flex items-start gap-2 text-on-surface-variant border border-surface-container-high/30">

          <span className="material-symbols-outlined text-[16px] text-outline mt-0.5 shrink-0">info</span>

          <p className="text-xs leading-relaxed text-outline">

            {language === 'mr'

              ? 'अगमार्कनेट मोडल लिलाव बंद भावांवर आधारित. मिनी ट्रक वाहतूक खर्च ₹१.८ प्रति किमी प्रति क्विंटल अधिक लोडिंग धरून मोजला आहे.'

              : 'Based on Agmarknet modal auction closing prices. Transport estimated via open mini-truck rates at ₹1.8/km/quintal with standard loading allowance.'}

          </p>

        </div>



        {/* Sticky Bottom Personalized Guidance Pill Card */}

        <div className="fixed bottom-0 left-0 right-0 p-3 bg-surface shadow-lg z-40 border-t border-surface-container-high">

          <div className="max-w-xl mx-auto">

            <button

              onClick={onOpenHarvestCalculator}

              className="w-full h-[54px] rounded-2xl bg-primary hover:bg-primary-container text-on-primary px-4 flex items-center justify-between shadow-md active:scale-[0.99] transition-all"

              type="button"

            >

              <div className="flex items-center gap-3 text-left">

                <div className="w-9 h-9 rounded-xl bg-surface-container-lowest/20 flex items-center justify-center shrink-0">

                  <span className="material-symbols-outlined text-[20px] text-on-primary">send</span>

                </div>

                <div>

                  <div className="text-sm font-bold flex items-center gap-1.5 leading-tight text-white">

                    <span>{language === 'mr' ? 'माझ्या पिकासाठी टेलिग्रामवर सल्ला घ्या' : 'Ask on Telegram for My Harvest'}</span>

                    <span className="material-symbols-outlined text-[16px]">arrow_forward</span>

                  </div>

                  <p className="text-xs text-primary-fixed opacity-90 leading-tight">

                    {language === 'mr'

                      ? 'तुमचे क्विंटल टाका आणि अचूक वेळ ठरवा'

                      : 'Enter your quintals & get custom timing'}

                  </p>

                </div>

              </div>

              <span className="material-symbols-outlined text-[22px] text-primary-fixed">forum</span>

            </button>

          </div>

        </div>



      </div>

    </div>

  );

};
