import React, { useState } from 'react';

import { Language, WeatherDay } from '../types';

import { ASSETS, CROPS_AFFECTED, SEVEN_DAY_FORECAST } from '../data/mockData';



interface WeatherScreenProps {

  language: Language;

  onOpenLocationModal: () => void;

  onOpenBotDrawer: (initialQuery?: string) => void;

  onNavigateToCropDetail: (cropId: string) => void;

}



export const WeatherScreen: React.FC<WeatherScreenProps> = ({

  language,

  onOpenLocationModal,

  onOpenBotDrawer,

  onNavigateToCropDetail,

}) => {

  const [selectedDayIndex, setSelectedDayIndex] = useState(0);

  const currentDay: WeatherDay = SEVEN_DAY_FORECAST[selectedDayIndex] || SEVEN_DAY_FORECAST[0];



  return (

    <div className="flex flex-col w-full pb-28 pt-16 max-w-xl mx-auto px-margin">

      <div className="pt-space-sm pb-space-lg flex flex-col gap-space-md">

        

        {/* Location & Live Status Strip */}

        <div className="flex items-center justify-between gap-space-sm bg-surface-container-lowest p-space-sm rounded-xl shadow-[0_4px_16px_rgba(31,42,31,0.04)] border border-surface-container-high/40">

          <button

            onClick={onOpenLocationModal}

            className="flex items-center gap-space-xs text-left min-w-0 group"

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

                <span className="font-title-md text-title-md text-on-surface truncate font-bold">

                  {language === 'mr' ? 'नाशिक, महाराष्ट्र' : 'Nashik, Maharashtra'}

                </span>

                <span className="material-symbols-outlined text-[16px] text-outline shrink-0 group-hover:translate-y-0.5 transition-transform">

                  expand_more

                </span>

              </div>

              <span className="font-label-sm text-label-sm text-on-surface-variant truncate">

                {language === 'mr' ? 'दिंडोरी तालुका • ब्लॉक ४बी' : 'Dindori Taluka • Block 4B'}

              </span>

            </div>

          </button>



          <div className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-secondary-container text-on-secondary-container shrink-0">

            <span className="inline-block w-2 h-2 rounded-full bg-primary animate-pulse"></span>

            <span className="font-label-sm text-label-sm font-semibold">

              {language === 'mr' ? '१० मि. पूर्वी अपडेट' : 'Updated 10m ago'}

            </span>

          </div>

        </div>



        <div className="rounded-2xl bg-surface-container-lowest border border-surface-container-high/70 p-4 shadow-[0_4px_16px_rgba(31,42,31,0.04)]">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[10px] uppercase tracking-wider text-primary font-bold">{language === 'hi' ? 'भाव पर असर' : language === 'mr' ? 'भावावर परिणाम' : 'Price impact'}</p>
              <h3 className="font-bold text-[15px] mt-1">{currentDay.rainChance >= 60 ? (language === 'hi' ? 'बारिश से खुले में ढुलाई का जोखिम बढ़ेगा' : language === 'mr' ? 'पावसामुळे उघड्या वाहतुकीचा धोका वाढेल' : 'Rain may raise open-transport risk') : (language === 'hi' ? 'मौसम सामान्य, मंडी आवक स्थिर' : language === 'mr' ? 'हवामान सामान्य, मंडी आवक स्थिर' : 'Weather is calm, mandi arrivals look steady')}</h3>
            </div>
            <span className={`px-2 py-1 rounded-full text-[10px] font-bold ${currentDay.rainChance >= 60 ? 'bg-[#fff9eb] text-tertiary' : 'bg-secondary-container text-on-secondary-container'}`}>{currentDay.rainChance >= 60 ? (language === 'hi' ? 'सावधानी' : language === 'mr' ? 'सावध' : 'CAUTION') : (language === 'hi' ? 'सामान्य' : language === 'mr' ? 'सामान्य' : 'NORMAL')}</span>
          </div>
          <p className="text-xs text-on-surface-variant mt-2">{currentDay.rainChance >= 60 ? (language === 'hi' ? 'गीली फसल से गुणवत्ता कटौती और परिवहन लागत बढ़ सकती है। बेचने से पहले मंडी सलाह देखें।' : language === 'mr' ? 'ओल्या मालामुळे गुणवत्ता कपात आणि वाहतूक खर्च वाढू शकतो. विक्रीपूर्वी मंडी सल्ला पाहा.' : 'Wet produce can mean quality deductions and higher transport costs. Check mandi advice before dispatch.') : (language === 'hi' ? 'मौसम से कीमत पर बड़ा दबाव नहीं दिख रहा। स्थानीय भाव और आवक देखते रहें।' : language === 'mr' ? 'हवामानामुळे भावावर मोठा दबाव दिसत नाही. स्थानिक भाव आणि आवक पाहत राहा.' : 'Weather is not showing a major price pressure. Keep watching local prices and arrivals.')}</p>
        </div>

        {/* Weather Hero Card with Ambient Imagery & Overlay */}

        <div className="relative overflow-hidden rounded-2xl bg-surface-container shadow-[0_8px_24px_rgba(31,42,31,0.08)]">

          <div

            className="w-full h-44 bg-cover bg-center transition-all duration-300"

            style={{ backgroundImage: `url('${ASSETS.weatherHeroBg}')` }}

          />

          <div className="absolute inset-0 bg-gradient-to-t from-inverse-surface via-inverse-surface/60 to-transparent"></div>



          {/* Temperature & Condition Callout inside Hero */}

          <div className="absolute inset-x-0 bottom-0 p-space-md flex flex-col justify-end text-inverse-on-surface">

            <div className="flex items-end justify-between">

              <div className="flex flex-col">

                <div className="flex items-baseline gap-1">

                  <span className="font-headline-xl text-[44px] leading-tight font-extrabold tracking-tight">

                    {currentDay.tempMax}°

                  </span>

                  <span className="font-title-lg text-title-lg text-secondary-fixed font-bold">C</span>

                </div>

                <p className="font-body-md text-body-md font-medium text-inverse-on-surface/90">

                  {language === 'mr'

                    ? `जाणवणारे तापमान ${currentDay.tempMax + 3}°C • दमट वारे`

                    : `Feels like ${currentDay.tempMax + 3}°C • Humid Breeze`}

                </p>

              </div>



              <div className="flex flex-col items-end text-right">

                <span

                  className="material-symbols-outlined text-[36px] text-secondary-fixed"

                  style={{ fontVariationSettings: "'FILL' 1" }}

                >

                  {currentDay.conditionIcon}

                </span>

                <span className="font-label-md text-label-md text-secondary-fixed font-semibold mt-0.5">

                  {currentDay.dayLabel[language]} • {currentDay.conditionIcon === 'rainy' ? (language === 'mr' ? 'अंशतः ढगाळ' : 'Partly Cloudy') : (language === 'mr' ? 'सूर्यप्रकाश' : 'Clear Sky')}

                </span>

              </div>

            </div>

          </div>

        </div>



        {/* Key Metrics 4-Grid */}

        <div className="grid grid-cols-2 gap-space-sm">

          {/* Rain Chance */}

          <div className="bg-surface-container-lowest p-space-sm rounded-xl shadow-[0_2px_12px_rgba(31,42,31,0.04)] flex items-center gap-3 border border-surface-container-high/40">

            <div className="w-10 h-10 rounded-full bg-secondary-container flex items-center justify-center text-primary shrink-0">

              <span className="material-symbols-outlined text-[20px]">rainy</span>

            </div>

            <div className="flex flex-col">

              <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider text-[11px]">

                {language === 'mr' ? 'पावसाची शक्यता' : 'Rain Chance'}

              </span>

              <span className="font-title-md text-title-md text-on-surface font-bold">

                {currentDay.rainChance}%{' '}

                <span className="font-label-sm text-label-sm font-normal text-error">

                  {currentDay.rainChance > 50 ? (language === 'mr' ? 'जास्त' : 'High') : (language === 'mr' ? 'कमी' : 'Low')}

                </span>

              </span>

            </div>

          </div>



          {/* Humidity */}

          <div className="bg-surface-container-lowest p-space-sm rounded-xl shadow-[0_2px_12px_rgba(31,42,31,0.04)] flex items-center gap-3 border border-surface-container-high/40">

            <div className="w-10 h-10 rounded-full bg-surface-variant flex items-center justify-center text-primary shrink-0">

              <span className="material-symbols-outlined text-[20px]">humidity_percentage</span>

            </div>

            <div className="flex flex-col">

              <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider text-[11px]">

                {language === 'mr' ? 'हवेतील आर्द्रता' : 'Humidity'}

              </span>

              <span className="font-title-md text-title-md text-on-surface font-bold">

                {currentDay.humidity}%

              </span>

            </div>

          </div>



          {/* Wind Speed */}

          <div className="bg-surface-container-lowest p-space-sm rounded-xl shadow-[0_2px_12px_rgba(31,42,31,0.04)] flex items-center gap-3 border border-surface-container-high/40">

            <div className="w-10 h-10 rounded-full bg-secondary-container flex items-center justify-center text-primary shrink-0">

              <span className="material-symbols-outlined text-[20px]">air</span>

            </div>

            <div className="flex flex-col">

              <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider text-[11px]">

                {language === 'mr' ? 'वाऱ्याचा वेग' : 'Wind Speed'}

              </span>

              <span className="font-title-md text-title-md text-on-surface font-bold">

                {currentDay.windSpeed} km/h{' '}

                <span className="font-label-sm text-label-sm font-normal text-outline">

                  {currentDay.windDirection}

                </span>

              </span>

            </div>

          </div>



          {/* Soil Moisture */}

          <div className="bg-surface-container-lowest p-space-sm rounded-xl shadow-[0_2px_12px_rgba(31,42,31,0.04)] flex items-center gap-3 border border-surface-container-high/40">

            <div className="w-10 h-10 rounded-full bg-surface-variant flex items-center justify-center text-primary shrink-0">

              <span className="material-symbols-outlined text-[20px]">water_drop</span>

            </div>

            <div className="flex flex-col">

              <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider text-[11px]">

                {language === 'mr' ? 'मातीतील ओलावा' : 'Soil Moisture'}

              </span>

              <span className="font-title-md text-title-md text-on-surface font-bold">

                {currentDay.soilMoisture}%{' '}

                <span className="font-label-sm text-label-sm font-normal text-primary">

                  {language === 'mr' ? 'संपृक्त' : currentDay.soilStatus}

                </span>

              </span>

            </div>

          </div>

        </div>



        {/* Weather Advisory Banner */}

        <div className="bg-error-container text-on-error-container p-space-md rounded-2xl flex items-start gap-space-sm shadow-[0_4px_16px_rgba(186,26,26,0.08)] border border-error/20">

          <span

            className="material-symbols-outlined text-[24px] text-error shrink-0 mt-0.5"

            style={{ fontVariationSettings: "'FILL' 1" }}

          >

            warning

          </span>

          <div className="flex flex-col">

            <span className="font-title-md text-title-md font-bold text-on-error-container">

              {language === 'mr' ? 'तातडीचा ४८-तास काढणी इशारा' : 'Critical 48-Hour Harvest Alert'}

            </span>

            <p className="font-body-md text-body-md text-on-error-container/90 mt-1 leading-relaxed text-[13px]">

              {language === 'mr'

                ? 'दिंडोरी खोऱ्यात अवेळी पाऊस आणि जमिनीतील जास्त ओलाव्यामुळे कांदा साठवणुकीत सड आणि बुरशीजन्य रोगांचा मोठा धोका आहे.'

                : 'High fungal disease and storage bulb rot risk across Dindori valley due to unseasonal post-harvest showers and saturated ground.'}

            </p>

          </div>

        </div>



        {/* Crops Affected Section */}

        <div className="flex flex-col gap-space-sm mt-2">

          <div className="flex items-center justify-between">

            <div className="flex items-center gap-1.5">

              <span className="material-symbols-outlined text-[20px] text-primary">eco</span>

              <h2 className="font-title-lg text-title-lg text-on-surface font-bold">

                {language === 'mr' ? 'हवामानाचा प्रभाव असणारी पिके' : language === 'hi' ? 'मौसम से प्रभावित फसलें' : 'Crops Affected by Weather'}

              </h2>

            </div>

            <span className="font-label-sm text-label-sm text-primary font-semibold">

              {language === 'mr' ? '४ पिकांचे निरीक्षण' : '4 Monitored'}

            </span>

          </div>



          {CROPS_AFFECTED.map((crop: any) => (

            <div

              key={crop.id}

              onClick={() => onNavigateToCropDetail(crop.id)}

              className="bg-surface-container-lowest p-space-md rounded-2xl shadow-[0_4px_16px_rgba(31,42,31,0.05)] border border-surface-container-high/40 flex flex-col gap-space-sm hover:border-primary/40 transition-colors cursor-pointer"

            >

              <div className="flex items-start justify-between gap-space-sm">

                <div className="flex items-center gap-space-sm">

                  <div

                    className="w-12 h-12 rounded-xl bg-cover bg-center shrink-0 shadow-xs"

                    style={{ backgroundImage: `url('${crop.imageUrl}')` }}

                  />

                  <div>

                    <h3 className="font-title-md text-title-md text-on-surface font-bold">

                      {crop.name[language]}

                    </h3>

                    <p className="font-label-sm text-label-sm text-on-surface-variant">

                      {crop.plot} • {crop.stage[language]}

                    </p>

                  </div>

                </div>



                <span

                  className={`px-2.5 py-1 rounded-full text-xs font-bold shrink-0 ${

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



              <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed text-[13px]">

                {crop.description[language]}

              </p>



              {crop.actionLabel && (

                <div className="bg-surface-container p-space-sm rounded-xl flex items-center justify-between">

                  <div className="flex items-center gap-2">

                    <span className="material-symbols-outlined text-[18px] text-primary">

                      {crop.actionType === 'dispatch' ? 'local_shipping' : crop.actionType === 'spray' ? 'science' : 'info'}

                    </span>

                    <span className="font-label-md text-label-md text-on-surface font-medium text-xs">

                      {crop.actionLabel[language]}

                    </span>

                  </div>

                  <span

                    className={`font-label-md text-label-md font-bold text-xs ${

                      crop.actionType === 'dispatch'

                        ? 'text-error'

                        : crop.actionType === 'spray'

                        ? 'text-tertiary'

                        : 'text-primary'

                    }`}

                  >

                    {crop.actionValue[language]}

                  </span>

                </div>

              )}

            </div>

          ))}

        </div>



        {/* 7-Day Agronomic Forecast Section */}

        <div className="flex flex-col gap-space-sm mt-3">

          <div className="flex items-center justify-between">

            <div className="flex items-center gap-1.5">

              <span className="material-symbols-outlined text-[20px] text-primary">calendar_month</span>

              <h2 className="font-title-lg text-title-lg text-on-surface font-bold">

                {language === 'mr' ? '७-दिवसीय कृषी अंदाज' : '7-Day Agronomic Outlook'}

              </h2>

            </div>

            <span className="font-label-sm text-label-sm text-outline">

              {language === 'mr' ? 'नाशिक मंडी विभाग' : 'Nashik Mandi Zone'}

            </span>

          </div>



          {/* Horizontal Daily Scroller */}

          <div className="flex gap-2.5 overflow-x-auto pb-1 -mx-margin px-margin no-scrollbar">

            {SEVEN_DAY_FORECAST.map((forecast: any, idx: number) => {

              const isSelected = selectedDayIndex === idx;

              return (

                <button

                  key={forecast.day}

                  onClick={() => setSelectedDayIndex(idx)}

                  type="button"

                  className={`flex flex-col items-center p-3 rounded-2xl min-w-[76px] shrink-0 transition-all ${

                    isSelected

                      ? 'bg-primary text-on-primary shadow-[0_4px_12px_rgba(80,96,77,0.25)] scale-105'

                      : 'bg-surface-container-lowest text-on-surface shadow-[0_2px_8px_rgba(31,42,31,0.04)] border border-surface-container-high/40 hover:bg-surface-container-low'

                  }`}

                >

                  <span className={`font-label-sm text-xs uppercase tracking-wider ${isSelected ? 'opacity-90 font-bold' : 'text-on-surface-variant'}`}>

                    {forecast.dayLabel[language]}

                  </span>

                  <span

                    className={`material-symbols-outlined text-[24px] my-2 ${

                      isSelected ? 'text-secondary-fixed' : forecast.rainMm > 10 ? 'text-primary' : 'text-secondary'

                    }`}

                  >

                    {forecast.conditionIcon}

                  </span>

                  <span className="font-title-md text-title-md font-bold text-[15px]">

                    {forecast.tempMax}°

                  </span>

                  <span className={`font-label-sm text-xs ${isSelected ? 'opacity-80' : 'text-outline'}`}>

                    {forecast.tempMin}°

                  </span>

                  <span

                    className={`mt-2 text-[10px] px-1.5 py-0.5 rounded-full font-semibold ${

                      isSelected

                        ? 'bg-on-primary/20 text-white'

                        : forecast.rainMm > 15

                        ? 'bg-secondary-container text-on-secondary-container'

                        : 'bg-surface-container text-on-surface-variant'

                    }`}

                  >

                    {forecast.rainMm} mm

                  </span>

                </button>

              );

            })}

          </div>



          {/* Mandi Logistics Safety Index Card */}

          <div className="bg-surface-container-lowest p-space-md rounded-2xl shadow-[0_4px_16px_rgba(31,42,31,0.04)] border border-surface-container-high/40 flex flex-col gap-3 mt-1">

            <div className="flex items-center justify-between">

              <div className="flex items-center gap-2">

                <span className="material-symbols-outlined text-[20px] text-primary">rv_hookup</span>

                <span className="font-title-md text-title-md text-on-surface font-bold text-[15px]">

                  {language === 'mr' ? 'मंडी वाहतूक सुरक्षितता निर्देशांक' : 'Mandi Logistics Safety Index'}

                </span>

              </div>

              <span className="font-label-md text-label-md px-2 py-0.5 rounded-full bg-secondary-container text-on-secondary-container font-bold text-xs">

                {language === 'mr' ? '८/१० (शुक्रवारपासून)' : '8/10 from Friday'}

              </span>

            </div>



            <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed text-[13px]">

              {language === 'mr'

                ? 'लासलगाव व पिंपळगाव मंड्यांकडे उघड्या ट्रॅक्टर व ट्रकने माल नेल्यास आज व बुधवारी पावसाने नुकसान होण्याचा मोठा धोका आहे. शुक्रवार सकाळपासून सुरक्षित वाहतूक सुरू करता येईल.'

                : 'Open-top tractor and truck freight to Lasalgaon & Pimpalgaon mandis is at high risk of water-damage today and Wednesday. Best window for dry road transport opens Friday morning.'}

            </p>



            {/* Inline Rainfall Bar Visualizer */}

            <div className="bg-surface-container p-space-sm rounded-xl flex flex-col gap-2">

              <div className="flex justify-between items-center text-on-surface-variant font-label-sm text-xs">

                <span>{language === 'mr' ? 'पाऊस प्रमाण आलेख' : 'Rain Volume Curve'}</span>

                <span className="font-semibold text-primary">

                  {language === 'mr' ? 'कमाल: बुध २४ मिमी' : 'Peak: Wed 24mm'}

                </span>

              </div>



              <div className="flex items-end gap-2 h-14 pt-2">

                {/* Tue */}

                <div className="flex-1 flex flex-col items-center gap-1 h-full justify-end">

                  <div className="w-full bg-secondary rounded-t-sm" style={{ height: '60%' }}></div>

                  <span className="font-label-sm text-[10px] text-outline">Tue</span>

                </div>

                {/* Wed (Peak - Red) */}

                <div className="flex-1 flex flex-col items-center gap-1 h-full justify-end">

                  <div className="w-full bg-error rounded-t-sm" style={{ height: '95%' }}></div>

                  <span className="font-label-sm text-[10px] text-error font-bold">Wed</span>

                </div>

                {/* Thu */}

                <div className="flex-1 flex flex-col items-center gap-1 h-full justify-end">

                  <div className="w-full bg-secondary-container rounded-t-sm" style={{ height: '25%' }}></div>

                  <span className="font-label-sm text-[10px] text-outline">Thu</span>

                </div>

                {/* Fri */}

                <div className="flex-1 flex flex-col items-center gap-1 h-full justify-end">

                  <div className="w-full bg-surface-variant rounded-t-sm" style={{ height: '6%' }}></div>

                  <span className="font-label-sm text-[10px] text-primary font-bold">Fri</span>

                </div>

                {/* Sat */}

                <div className="flex-1 flex flex-col items-center gap-1 h-full justify-end">

                  <div className="w-full bg-surface-variant rounded-t-sm" style={{ height: '4%' }}></div>

                  <span className="font-label-sm text-[10px] text-outline">Sat</span>

                </div>

                {/* Sun */}

                <div className="flex-1 flex flex-col items-center gap-1 h-full justify-end">

                  <div className="w-full bg-surface-variant rounded-t-sm" style={{ height: '4%' }}></div>

                  <span className="font-label-sm text-[10px] text-outline">Sun</span>

                </div>

              </div>

            </div>

          </div>

        </div>



        {/* Direct CTA Banner for Bot Interaction */}

        <button

          onClick={() => onOpenBotDrawer('How does the rain alter my onion price and dispatch window?')}

          className="bg-primary hover:bg-primary-container text-on-primary p-space-md rounded-2xl flex items-center justify-between gap-space-sm shadow-[0_6px_20px_rgba(80,96,77,0.22)] active:scale-[0.99] transition-all text-left"

          type="button"

        >

          <div className="flex items-center gap-space-sm min-w-0">

            <div className="w-11 h-11 rounded-full bg-primary-container flex items-center justify-center text-on-primary shrink-0">

              <span className="material-symbols-outlined text-[22px]">smart_toy</span>

            </div>

            <div className="flex flex-col min-w-0">

              <span className="font-title-md text-title-md font-bold truncate text-on-primary">

                {language === 'mr' ? 'SHETBHAV बॉटकडे विचारा' : language === 'hi' ? 'SHETBHAV से पूछें' : 'Ask SHETBHAV Bot'}

              </span>

              <span className="font-body-md text-[13px] text-primary-fixed truncate">

                {language === 'mr'

                  ? 'पावसामुळे पिकांच्या भावावर होणारा परिणाम तपासा →'

                  : 'Calculate how rain alters your crop price →'}

              </span>

            </div>

          </div>

          <span className="material-symbols-outlined text-[24px] text-primary-fixed shrink-0">

            send

          </span>

        </button>



      </div>

    </div>

  );

};
