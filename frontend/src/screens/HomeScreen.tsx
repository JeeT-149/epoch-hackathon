import React, { useState } from 'react';

import { ScreenType, Language } from '../types';
import { ASSETS, TRENDING_CROPS } from '../data/mockData';
import { InfiniteSlider } from '@/components/ui/infinite-slider';



interface HomeScreenProps {

  language: Language;

  onNavigate: (screen: ScreenType) => void;


  onOpenRouteModal: () => void;

  onOpenLocationModal: () => void;

  onOpenTelegramModal: () => void;
  onOpenCropScan: () => void;

}



export const HomeScreen: React.FC<HomeScreenProps> = ({

  language,

  onNavigate,


  onOpenRouteModal,

  onOpenLocationModal,

  onOpenTelegramModal,
  onOpenCropScan,

}) => {

  const [selectedTrendingIndex, setSelectedTrendingIndex] = useState<number | null>(null);



  return (

    <div className="flex flex-col w-full pb-28 pt-16 max-w-xl mx-auto px-margin">
      <button type="button" onClick={onOpenCropScan} className="mt-3 mb-2 w-full rounded-2xl bg-secondary-container text-on-secondary-container p-4 flex items-center justify-between text-left shadow-xs"><span className="flex items-center gap-3"><span className="w-10 h-10 rounded-xl bg-primary text-on-primary flex items-center justify-center"><span className="material-symbols-outlined">photo_camera</span></span><span><strong className="block text-sm">{language === 'mr' ? 'पिकाचा फोटो तपासा' : language === 'hi' ? 'फसल का फोटो जांचें' : 'Check your crop photo'}</strong><span className="block text-[11px] mt-0.5">{language === 'mr' ? 'पिकण्याची अवस्था, नुकसान आणि विक्रीची वेळ' : language === 'hi' ? 'पकने, नुकसान और बेचने का समय' : 'Ripeness, damage, and when to sell'}</span></span></span><span className="material-symbols-outlined">chevron_right</span></button>

      {/* Live Location Strip */}

      <div className="pt-space-sm pb-space-sm">

        <div className="flex items-center justify-between gap-space-sm bg-surface-container-lowest p-space-sm rounded-xl shadow-[0_2px_12px_rgba(31,42,31,0.04)] border border-surface-container-high/40">

          <button

            onClick={onOpenLocationModal}

            className="flex items-center gap-2 text-left min-w-0 group"

            type="button"

          >

            <span

              className="material-symbols-outlined text-[20px] text-primary shrink-0"

              style={{ fontVariationSettings: "'FILL' 1" }}

            >

              location_on

            </span>

            <div className="flex flex-col min-w-0">

              <div className="flex items-center gap-1">

                <span className="font-title-md text-[15px] font-bold text-on-surface truncate">

                  {language === 'mr' ? 'नाशिक, महाराष्ट्र' : 'Nashik, Maharashtra'}

                </span>

                <span className="material-symbols-outlined text-[16px] text-outline shrink-0 group-hover:translate-y-0.5 transition-transform">

                  expand_more

                </span>

              </div>

              <span className="text-[11px] text-on-surface-variant truncate">

                {language === 'mr' ? 'थेट बाजार भाव • दिंडोरी तालुका' : language === 'hi' ? 'सीधे मंडी भाव • दिंडोरी तालुका' : 'Live Mandi Feed • Dindori Taluka'}

              </span>

            </div>

          </button>



          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-secondary-container text-on-secondary-container shrink-0">

            <span className="inline-block w-2 h-2 rounded-full bg-primary animate-pulse"></span>

            <span className="text-[11px] font-semibold">{language === 'mr' ? 'सुरू आहे' : language === 'hi' ? 'सक्रिय' : 'Active'}</span>

          </div>

        </div>

      </div>



      {/* Greeting Section */}

      <div className="pt-2 pb-3">

        <h2 className="text-[26px] font-extrabold text-on-surface tracking-tight leading-tight">

          {language === 'mr' ? 'नमस्ते, रमेश 🙏' : 'Namaste, Ramesh 🙏'}

        </h2>

        <p className="text-[15px] text-on-surface-variant font-medium mt-0.5">

          {language === 'mr' ? 'आज आपण काय विकत आहात?' : language === 'hi' ? 'आज आप क्या बेच रहे हैं?' : 'What are you selling today?'}

        </p>

      </div>



      {/* Telegram Advisor Banner (Warm Honey/Gold Gradient) */}

      <button

        onClick={onOpenTelegramModal}

        className="w-full text-left bg-gradient-to-r from-[#EBB02D] via-[#F3B737] to-[#DF9E1B] text-[#221B0B] p-4 rounded-2xl shadow-[0_6px_20px_rgba(235,176,45,0.28)] flex items-center justify-between gap-3 active:scale-[0.99] transition-transform my-1"

        type="button"

      >

        <div className="flex items-center gap-3 min-w-0">

          <div className="w-10 h-10 rounded-full bg-[#1F2A1F]/15 flex items-center justify-center text-[#1F2A1F] shrink-0 font-bold">

            <span className="material-symbols-outlined text-[22px]">send</span>

          </div>

          <div className="flex flex-col min-w-0">

            <div className="flex items-center gap-1 font-bold text-[15px] text-[#1F2A1F] truncate">

              <span>{language === 'mr' ? 'टेलिग्रामवर SHETBHAV शी बोला' : 'Chat with SHETBHAV on Telegram'}</span>

              <span className="material-symbols-outlined text-[16px]">chevron_right</span>

            </div>

            <p className="text-[12px] font-medium text-[#1F2A1F]/90 truncate mt-0.5 underline underline-offset-2">

              {language === 'mr'

                ? 'विक्री / थांबा / बाजार बदल सल्ला मराठीत मिळवा'

                : 'Get sell / wait / switch advice in मराठी, Hindi & EN'}

            </p>

          </div>

        </div>

        <div className="w-8 h-8 rounded-full bg-[#1F2A1F]/10 flex items-center justify-center shrink-0">

          <span className="material-symbols-outlined text-[18px]">chevron_right</span>

        </div>

      </button>



      {/* Trending in Mandis Today */}

      <div className="mt-5 flex flex-col gap-2">

        <div className="flex items-center justify-between">

          <div>

            <h3 className="text-[18px] font-bold text-on-surface">

              {language === 'mr' ? 'आज बाजारातील कल' : language === 'hi' ? 'आज मंडी में चलन' : 'Trending in mandis today'}

            </h3>

            <p className="text-[11px] text-on-surface-variant">

              {language === 'mr' ? 'थेट अपडेट्स • नाशिक एपीएमसी' : 'Auto-updates live • Nashik APMC'}

            </p>

          </div>

          <button

            onClick={() => onNavigate('markets')}

            className="px-2.5 py-1 rounded-full bg-surface-container-high text-primary font-semibold text-xs hover:bg-surface-container-highest transition-colors"

            type="button"

          >

            {language === 'mr' ? 'सर्व पहा (१८)' : 'See all (18)'}

          </button>

        </div>



        {/* Moving Carousel via InfiniteSlider */}
        <div className="pt-1 -mx-margin px-margin overflow-hidden">
          <InfiniteSlider gap={12} duration={25} durationOnHover={75} className="w-full py-1">
            {TRENDING_CROPS.map((crop: any, index: number) => {
              const isSelected = selectedTrendingIndex === index;

              return (
                <div
                  key={crop.id}
                  onClick={() => {
                    setSelectedTrendingIndex(index);
                    if (crop.id === 'crop-onion') {
                      onNavigate('mandi-details');
                    }
                  }}
                  className={`min-w-[140px] p-3 rounded-2xl bg-surface-container-lowest border transition-all cursor-pointer shadow-xs select-none ${
                    isSelected
                      ? 'border-primary ring-2 ring-primary/20 scale-[1.02]'
                      : 'border-surface-container-high/60 hover:border-primary/50'
                  }`}
                >
                  <div className="flex items-center justify-between gap-1">
                    <img
                      src={crop.imageUrl}
                      alt={crop.name.en}
                      className="w-9 h-9 rounded-full object-cover shadow-xs border border-surface-container-high/40"
                    />
                    <div className="flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-secondary-container text-on-secondary-container text-[10px] font-bold">
                      <span>▲</span>
                      <span>{crop.deltaPercent}%</span>
                    </div>
                  </div>

                  <div className="mt-2">
                    <h4 className="font-bold text-[14px] text-on-surface truncate">
                      {crop.name[language]}
                    </h4>
                    <p className="text-[11px] text-on-surface-variant truncate">{crop.variety}</p>
                  </div>

                  <div className="mt-1.5 flex items-baseline justify-between">
                    <span className="text-[15px] font-extrabold text-on-surface">
                      ₹{crop.modalPrice.toLocaleString()}<span className="text-[10px] font-normal text-outline">/q</span>
                    </span>
                    {/* Micro sparkline matching screenshot */}
                    <svg className="w-8 h-3 text-secondary" viewBox="0 0 32 12" fill="none">
                      <path
                        d="M1 9 C 8 8, 14 11, 20 5 S 28 2, 31 1"
                        stroke="#4c6546"
                        strokeWidth="2"
                        strokeLinecap="round"
                      />
                    </svg>
                  </div>
                </div>
              );
            })}
          </InfiniteSlider>
        </div>

        <p className="text-[11px] text-center text-outline mt-1">
          {language === 'mr'
            ? '⇄ थेट पट्टी सरकवा • संपूर्ण मंडी माहितीसाठी पिकावर टॅप करा'
            : '⇄ sliding live ticker • tap any crop for full mandi comparison'}
        </p>
      </div>



      {/* For You Near Nashik - Smart Dispatch */}

      <div className="mt-6 flex flex-col gap-3">

        <div className="flex items-center justify-between">

          <div className="flex items-center gap-1.5">

            <span className="w-2.5 h-2.5 rounded-full bg-primary inline-block"></span>

            <h3 className="text-[18px] font-bold text-on-surface">

              {language === 'mr' ? 'नाशिक जवळ तुमच्यासाठी' : 'For you near Nashik'}

            </h3>

          </div>

          <span className="text-xs font-semibold text-primary">

            {language === 'mr' ? 'स्मार्ट पाठवणूक' : 'Smart Dispatch'}

          </span>

        </div>



        {/* Card 1: Onion Wait 5 Days */}

        <div className="bg-surface-container-lowest rounded-2xl overflow-hidden shadow-[0_4px_16px_rgba(31,42,31,0.06)] border border-surface-container-high/40">

          {/* Image with badges */}

          <div className="relative w-full h-44 bg-surface-container">

            <img

              src={ASSETS.onionSacksHero}

              alt="Fresh red onions in sacks at Lasalgaon"

              className="w-full h-full object-cover object-center"

            />

            <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent"></div>



            {/* Top Badge: WAIT 5 DAYS */}

            <div className="absolute top-3 left-3 bg-[#D4E8CE] text-[#1E3E1C] px-3 py-1 rounded-full text-xs font-extrabold tracking-wide uppercase shadow-sm">

              {language === 'mr' ? '५ दिवस थांबा' : 'WAIT 5 DAYS'}

            </div>



            {/* Bottom Overlay Info */}

            <div className="absolute bottom-2.5 inset-x-3 flex items-center justify-between text-white">

              <span className="text-xs font-semibold drop-shadow-sm bg-black/70 px-2 py-0.5 rounded-md">

                {language === 'mr' ? 'लासलगाव एपीएमसी' : 'Lasalgaon APMC'}

              </span>

              <div className="px-2.5 py-1 rounded-full bg-[#526B4C] text-[#F7FFF1] text-xs font-bold shadow-sm">

                {language === 'mr' ? 'अपेक्षित नफा: +₹१८०/क्विं' : 'Expected Gain: +₹180/qtl'}

              </div>

            </div>

          </div>



          {/* Content Body */}

          <div className="p-4 flex flex-col gap-3">

            <div>

              <h4 className="text-[17px] font-bold text-on-surface">

                {language === 'mr'

                  ? 'कांदा: ५ दिवस थांबा, संभाव्य नफा ₹१८०/क्विंटल'

                  : 'Onion: Wait 5 days, likely gain ₹180/quintal'}

              </h4>

              <p className="text-[13px] text-on-surface-variant mt-1 leading-relaxed">

                {language === 'mr'

                  ? 'निर्यात जहाजे पोहोचल्याने लासलगाव मंडीचा सरासरी भाव ₹१,४२० वरून ₹१,६०० पर्यंत वाढण्याची शक्यता.'

                  : 'Lasalgaon Mandi modal price expected to rise from ₹1,420 to ₹1,600 due to export vessel arrivals.'}

              </p>

            </div>



            {/* 3 Metric Pills */}

            <div className="grid grid-cols-3 gap-2 bg-surface-container-low p-2.5 rounded-xl text-center">

              <div>

                <span className="text-[10px] uppercase font-semibold text-outline">

                  {language === 'mr' ? 'आजचा भाव' : "Today's Modal"}

                </span>

                <p className="text-[14px] font-bold text-on-surface mt-0.5">₹1,420/q</p>

              </div>

              <div className="border-x border-outline-variant/40">

                <span className="text-[10px] uppercase font-semibold text-secondary">

                  {language === 'mr' ? '५ दिवसांनंतर' : 'Day 5 Forecast'}

                </span>

                <p className="text-[14px] font-bold text-secondary mt-0.5">₹1,600/q</p>

              </div>

              <div>

                <span className="text-[10px] uppercase font-semibold text-outline">

                  {language === 'mr' ? 'साठवणूक धोका' : 'Storage Risk'}

                </span>

                <p className="text-[14px] font-bold text-primary mt-0.5">

                  {language === 'mr' ? 'कमी (कोरडे)' : 'Low (Dry)'}

                </p>

              </div>

            </div>



            {/* Primary Action Button */}

            <button

              onClick={() => onNavigate('mandi-details')}

              className="w-full h-12 rounded-xl bg-primary hover:bg-primary-container text-on-primary font-bold text-sm flex items-center justify-center gap-2 shadow-sm active:scale-[0.99] transition-all"

              type="button"

            >

              <span>{language === 'mr' ? 'नाशिक मंड्यांचे दर पहा' : 'View Nashik Mandis'}</span>

              <span className="material-symbols-outlined text-[18px]">arrow_forward</span>

            </button>

          </div>

        </div>



        {/* Card 2: Tomato Switch Market */}

        <div className="bg-surface-container-lowest rounded-2xl overflow-hidden shadow-[0_4px_16px_rgba(31,42,31,0.06)] border border-surface-container-high/40">

          <div className="relative w-full h-44 bg-surface-container">

            <img

              src={ASSETS.tomatoCrates}

              alt="Fresh tomatoes loaded in wooden crates"

              className="w-full h-full object-cover object-center"

            />

            <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent"></div>



            <div className="absolute top-3 left-3 bg-[#FFE7D9] text-[#7A2700] px-3 py-1 rounded-full text-xs font-extrabold tracking-wide uppercase shadow-sm">

              {language === 'mr' ? 'बाजार बदला' : 'SWITCH MARKET'}

            </div>



            <div className="absolute bottom-2.5 inset-x-3 flex items-center justify-between text-white">

              <span className="text-xs font-semibold drop-shadow-sm bg-black/70 px-2 py-0.5 rounded-md">

                {language === 'mr' ? 'पुणे विरुद्ध पिंपळगाव' : 'Pune vs Pimpalgaon'}

              </span>

              <div className="px-2.5 py-1 rounded-full bg-[#4C6546] text-[#F7FFF1] text-xs font-bold shadow-sm">

                {language === 'mr' ? 'अतिरिक्त निव्वळ नफा: +₹२४०/क्विं' : 'Net Extra: +₹240/qtl'}

              </div>

            </div>

          </div>



          <div className="p-4 flex flex-col gap-3">

            <div>

              <h4 className="text-[17px] font-bold text-on-surface">

                {language === 'mr' ? 'टोमॅटो: पुणे मंडीकडे माल वळवा' : 'Tomato: Switch to Pune mandi'}

              </h4>

              <p className="text-[13px] text-on-surface-variant mt-1 leading-relaxed">

                {language === 'mr'

                  ? '₹८० वाहतूक खर्च वजा केल्यानंतरही पुणे बाजार पिंपळगावपेक्षा ₹३२०/क्विंटल जास्त भाव देत आहे.'

                  : 'Pune paying +₹320/qtl more than Pimpalgaon after deducting ₹80 transport cost.'}

              </p>

            </div>



            <div className="grid grid-cols-3 gap-2 bg-surface-container-low p-2.5 rounded-xl text-center items-center">

              <div>

                <span className="text-[10px] uppercase font-semibold text-outline">

                  {language === 'mr' ? 'पिंपळगाव' : 'Pimpalgaon'}

                </span>

                <p className="text-[14px] font-bold text-on-surface mt-0.5">₹2,130/q</p>

              </div>

              <div className="flex flex-col items-center">

                <span className="text-primary font-bold text-[14px]">→</span>

                <span className="text-[10px] uppercase font-semibold text-secondary">

                  {language === 'mr' ? 'पुणे गुलटेकडी' : 'Pune Gultekdi'}

                </span>

                <p className="text-[14px] font-bold text-secondary">₹2,450/q</p>

              </div>

              <div>

                <span className="text-[10px] uppercase font-semibold text-outline">

                  {language === 'mr' ? 'अंतर' : 'Distance'}

                </span>

                <p className="text-[14px] font-bold text-on-surface mt-0.5">145 km</p>

              </div>

            </div>



            <button

              onClick={onOpenRouteModal}

              className="w-full h-12 rounded-xl bg-secondary-container hover:bg-secondary-container/80 text-on-secondary-container font-bold text-sm flex items-center justify-center gap-2 shadow-xs active:scale-[0.99] transition-all"

              type="button"

            >

              <span>{language === 'mr' ? 'मार्ग आणि ट्रक भाडे तपासा' : 'Compare Routes & Truck Rates'}</span>

              <span className="material-symbols-outlined text-[18px]">alt_route</span>

            </button>

          </div>

        </div>



        {/* Voice Search Card */}

        <div className="hidden">

          <div className="flex items-center gap-3">

            <button

              onClick={() => undefined}

              className="w-12 h-12 rounded-full bg-secondary-container text-primary flex items-center justify-center shrink-0 hover:scale-105 active:scale-95 transition-transform"

              type="button"

              aria-label="Voice Search"

            >

              <span className="material-symbols-outlined text-[24px]">mic</span>

            </button>

            <div className="flex flex-col">

              <h4 className="font-bold text-[15px] text-on-surface">

                {language === 'mr' ? 'बोलून मंडी भाव जाणून घ्या?' : 'Need mandi rates by voice?'}

              </h4>

              <p className="text-[12px] text-on-surface-variant">

                {language === 'mr' ? 'मराठी किंवा हिंदीमध्ये कधीही विचारा' : 'Speak in Marathi or Hindi anytime'}

              </p>

            </div>

          </div>



          <button

            onClick={() => undefined}

            className="w-10 h-10 rounded-full bg-primary text-on-primary flex items-center justify-center shrink-0 hover:bg-primary-container shadow-xs active:scale-95 transition-transform"

            type="button"

            aria-label="Activate voice mic"

          >

            <span className="material-symbols-outlined text-[20px]">graphic_eq</span>

          </button>

        </div>



        {/* Agmarknet Verification Footnote */}

        <div className="py-2 text-center text-outline">

          <div className="flex items-center justify-center gap-1.5 text-xs font-semibold text-on-surface-variant">

            <span className="material-symbols-outlined text-[15px] text-secondary">verified</span>

            <span>Agmarknet Verified Feed</span>

          </div>

          <p className="text-[11px] text-outline mt-0.5 leading-relaxed max-w-sm mx-auto">

            {language === 'mr'

              ? 'बाजार (मोडल) दरांवर आधारित. प्रत्यक्ष दर प्रतवारीनुसार बदलू शकतात. २० मिनिटांपूर्वी अपडेट केले.'

              : 'Based on market (modal) prices. Your actual price may differ. Data updated 20 mins ago from Agmarknet.'}

          </p>

        </div>

      </div>

    </div>

  );

};
