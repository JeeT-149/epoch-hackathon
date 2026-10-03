import React from 'react';

import { Language } from '../types';

import { ASSETS } from '../data/mockData';



interface ProfileScreenProps {

  language: Language;

  onLanguageChange: (lang: Language) => void;

  onOpenNotifications: () => void;

  onOpenLocationModal: () => void;

}



export const ProfileScreen: React.FC<ProfileScreenProps> = ({

  language,

  onLanguageChange,

  onOpenNotifications,

  onOpenLocationModal,

}) => {

  return (

    <div className="flex flex-col w-full pb-28 pt-16 max-w-xl mx-auto px-margin">

      {/* Profile Card */}

      <div className="p-4 rounded-2xl bg-surface-container-lowest border border-surface-container-high/60 shadow-sm mt-2 flex items-center gap-4">

        <img

          src={ASSETS.profileAvatar}

          alt="Ramesh Jadhav"

          className="w-16 h-16 rounded-full object-cover ring-2 ring-primary/40 shrink-0"

        />

        <div className="flex-1 min-w-0">

          <div className="flex items-center gap-1.5">

            <h2 className="text-[18px] font-bold text-on-surface truncate">

              {language === 'mr' ? 'रमेश जाधव' : language === 'hi' ? 'रमेश जाधव' : 'Ramesh Jadhav'}

            </h2>

            <span className="material-symbols-outlined text-[16px] text-secondary" style={{ fontVariationSettings: "'FILL' 1" }}>

              verified

            </span>

          </div>

          <p className="text-xs text-on-surface-variant">

            {language === 'mr' ? 'शेतकरी • दिंडोरी, नाशिक' : language === 'hi' ? 'प्रगतिशील किसान • दिंडोरी, नासिक' : 'Progressive Farmer • Dindori, Nashik'}

          </p>

          <div className="flex items-center gap-2 mt-1">

            <span className="text-[10px] px-2 py-0.5 rounded-full bg-secondary-container text-on-secondary-container font-semibold">

              {language === 'mr' ? '१८ एकर जमीन' : language === 'hi' ? '18 एकड़ जमीन' : '18 Acres Land'}

            </span>

            <span className="text-[10px] px-2 py-0.5 rounded-full bg-surface-container text-on-surface-variant font-semibold">

              Kisan ID: MH-NSK-4921

            </span>

          </div>

        </div>

      </div>



      {/* Language Preferences */}

      <div className="mt-4 p-4 rounded-2xl bg-surface-container-lowest border border-surface-container-high/60 shadow-xs">

        <h3 className="font-bold text-[15px] text-on-surface flex items-center gap-2">

          <span className="material-symbols-outlined text-[18px] text-primary">language</span>

          <span>{language === 'mr' ? 'अॅप भाषा निवडा' : language === 'hi' ? 'ऐप की भाषा' : 'App Language'}</span>

        </h3>

        <p className="text-xs text-on-surface-variant mt-0.5">

          {language === 'mr' ? 'हवामान, भाव आणि सल्ला मिळवण्यासाठी' : language === 'hi' ? 'बाज़ार, मौसम और सलाह के लिए' : 'For market alerts, weather, and AI bot guidance'}

        </p>



        <div className="grid grid-cols-3 gap-2 mt-3">

          <button

            onClick={() => onLanguageChange('mr')}

            className={`p-3 rounded-xl border text-center transition-all ${

              language === 'mr'

                ? 'border-primary bg-secondary-container/40 text-primary font-bold shadow-xs'

                : 'border-surface-container-high bg-surface-container-low text-on-surface-variant hover:bg-surface-container'

            }`}

            type="button"

          >

            <div className="text-sm font-bold">मराठी</div>

            <div className="text-[10px] opacity-75">Marathi Native</div>

          </button>

          <button
            onClick={() => onLanguageChange('hi')}
            className={`p-3 rounded-xl border text-center transition-all ${language === 'hi' ? 'border-primary bg-secondary-container/40 text-primary font-bold shadow-xs' : 'border-surface-container-high bg-surface-container-low text-on-surface-variant hover:bg-surface-container'}`}
            type="button"
          >
            <div className="text-sm font-bold">हिंदी</div>
            <div className="text-[10px] opacity-75">Hindi</div>
          </button>



          <button

            onClick={() => onLanguageChange('en')}

            className={`p-3 rounded-xl border text-center transition-all ${

              language === 'en'

                ? 'border-primary bg-secondary-container/40 text-primary font-bold shadow-xs'

                : 'border-surface-container-high bg-surface-container-low text-on-surface-variant hover:bg-surface-container'

            }`}

            type="button"

          >

            <div className="text-sm font-bold">English</div>

            <div className="text-[10px] opacity-75">English & Transliteration</div>

          </button>

        </div>

      </div>



      {/* Farm Location & Mandi Radius */}

      <div className="mt-4 p-4 rounded-2xl bg-surface-container-lowest border border-surface-container-high/60 shadow-xs">

        <div className="flex items-center justify-between">

          <div className="flex items-center gap-2">

            <span className="material-symbols-outlined text-[18px] text-primary">location_on</span>

            <h3 className="font-bold text-[15px] text-on-surface">

              {language === 'mr' ? 'शेत स्थान व अंतर' : 'Farm Location & Radius'}

            </h3>

          </div>

          <button

            onClick={onOpenLocationModal}

            className="text-xs font-bold text-primary hover:underline"

            type="button"

          >

            {language === 'mr' ? 'बदला' : 'Change'}

          </button>

        </div>



        <div className="mt-2.5 p-3 rounded-xl bg-surface-container text-xs flex items-center justify-between">

          <div>

            <p className="font-bold text-on-surface">Dindori Taluka, Block 4B</p>

            <p className="text-outline text-[11px]">Nashik District, Maharashtra</p>

          </div>

          <span className="px-2 py-1 rounded-lg bg-surface-container-lowest font-bold text-secondary text-[11px]">

            GPS Synced

          </span>

        </div>

      </div>



      {/* Telegram & WhatsApp Integration */}

      <div className="mt-4 p-4 rounded-2xl bg-surface-container-lowest border border-surface-container-high/60 shadow-xs">

        <h3 className="font-bold text-[15px] text-on-surface flex items-center gap-2">

          <span className="material-symbols-outlined text-[18px] text-primary">send</span>

          <span>{language === 'mr' ? 'थेट संदेश व अलर्ट' : 'Instant Message Alerts'}</span>

        </h3>

        <p className="text-xs text-on-surface-variant mt-0.5">

          {language === 'mr' ? 'टेलिग्राम आणि व्हॉट्सअॅपवर दररोज सकाळी ७ वाजता भाव मिळवा' : 'Receive 7 AM daily APMC alerts directly on Telegram'}

        </p>



        <div className="mt-3 flex items-center justify-between p-3 rounded-xl bg-[#EAF7E6] border border-[#CEEBC4]">

          <div className="flex items-center gap-2.5">

            <span className="material-symbols-outlined text-[20px] text-secondary">check_circle</span>

            <div>

              <p className="text-xs font-bold text-on-surface">@SHETBHAV_NashikBot</p>

              <p className="text-[11px] text-outline">Connected (+91 98220 •••••)</p>

            </div>

          </div>

          <span className="text-[11px] font-bold text-secondary">Active</span>

        </div>

      </div>



      {/* Notifications Shortcut */}

      <div className="mt-4">

        <button

          onClick={onOpenNotifications}

          className="w-full p-4 rounded-2xl bg-surface-container hover:bg-surface-container-high transition-colors flex items-center justify-between text-on-surface font-semibold text-xs sm:text-sm"

          type="button"

        >

          <div className="flex items-center gap-2">

            <span className="material-symbols-outlined text-[18px]">notifications_active</span>

            <span>{language === 'mr' ? 'अलीकडील सूचना व इशारे पहा' : 'View Recent Alerts & Weather Warnings'}</span>

          </div>

          <span className="material-symbols-outlined text-[18px]">chevron_right</span>

        </button>

      </div>

    </div>

  );

};
