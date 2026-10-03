import React from 'react';
import { ScreenType, Language } from '../types';
import { ASSETS } from '../data/mockData';

interface HeaderProps {
  currentScreen: ScreenType;
  language: Language;
  onLanguageChange: (language: Language) => void;
  onNavigate: (screen: ScreenType) => void;
  onOpenNotifications: () => void;
  onOpenProfile: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentScreen,
  language,
  onLanguageChange,
  onNavigate,
  onOpenNotifications,
  onOpenProfile,
}) => {
  const getScreenTitle = () => {
    switch (currentScreen) {
      case 'home':
        return language === 'mr' ? 'मुख्य पान' : language === 'hi' ? 'होम' : 'Home';
      case 'weather':
        return language === 'mr' ? 'हवामान' : language === 'hi' ? 'मौसम' : 'Weather';
      case 'mandi-details':
        return language === 'mr' ? 'मंडी तपशील' : language === 'hi' ? 'मंडी विवरण' : 'Mandi Details';
      case 'chats':
        return language === 'mr' ? 'सल्ला' : language === 'hi' ? 'सलाह' : 'Advice';
      case 'my-crops':
        return language === 'mr' ? 'माझी पिके' : language === 'hi' ? 'मेरी फसल' : 'My Crops';
      case 'markets':
        return language === 'mr' ? 'बाजार समित्या' : language === 'hi' ? 'मंडियां' : 'Markets';
      case 'evidence':
        return language === 'mr' ? 'विश्वास आणि पुरावा' : language === 'hi' ? 'भरोसा और सबूत' : 'Trust & Evidence';
      case 'profile':
        return language === 'mr' ? 'प्रोफाइल' : language === 'hi' ? 'प्रोफाइल' : 'Profile';
      case 'crop-scan':
        return language === 'mr' ? 'पिकाची तपासणी' : language === 'hi' ? 'फसल की जांच' : 'Crop check';
      default:
        return 'SHETBHAV';
    }
  };

  const isStackScreen = currentScreen === 'mandi-details';

  return (
    <header className="fixed top-0 w-full z-50 pt-safe bg-surface border-b border-surface-container-high shadow-sm">
      <div className="h-16 px-margin max-w-xl mx-auto flex items-center justify-between gap-space-sm">
        <div className="flex items-center gap-space-sm min-w-0">
          {isStackScreen ? (
            <button
              onClick={() => onNavigate('home')}
              className="w-10 h-10 flex items-center justify-center rounded-full bg-surface-container text-on-surface hover:bg-surface-container-high transition-colors active:scale-95 shrink-0"
              type="button"
              aria-label="Go back"
            >
              <span className="material-symbols-outlined text-[20px]">arrow_back_ios_new</span>
            </button>
          ) : null}

          <div 
            onClick={() => onNavigate('home')}
            className="flex items-center gap-2 cursor-pointer group min-w-0"
          >
            <img
              src={ASSETS.logo}
              alt="SHETBHAV logo"
              className="h-10 w-10 rounded-lg object-contain shrink-0 group-hover:scale-105 transition-transform"
            />
            <div className="flex flex-col truncate">
              <span className="font-label-sm text-[11px] text-primary uppercase tracking-wider font-semibold leading-tight">
                SHETBHAV
              </span>
              <h1 className="font-title-md text-[16px] text-on-surface truncate leading-tight font-bold">
                {getScreenTitle()}
              </h1>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <label className="flex items-center gap-1 px-2 py-1 rounded-full bg-secondary-container text-on-secondary-container text-xs font-semibold border border-secondary/20">
            <span className="material-symbols-outlined text-[16px]">translate</span>
            <select aria-label="Language" value={language} onChange={(event) => onLanguageChange(event.target.value as Language)} className="bg-transparent outline-none cursor-pointer max-w-[78px]">
              <option value="en">English</option>
              <option value="hi">हिंदी</option>
              <option value="mr">मराठी</option>
            </select>
          </label>

          {/* Notifications button */}
          <button
            onClick={onOpenNotifications}
            className="w-10 h-10 rounded-full flex items-center justify-center text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors relative"
            type="button"
            aria-label="Notifications"
          >
            <span className="material-symbols-outlined text-[22px]">notifications</span>
            <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-error ring-2 ring-surface"></span>
          </button>

          {/* Profile button */}
          <button
            onClick={onOpenProfile}
            className="w-9 h-9 rounded-full overflow-hidden ring-2 ring-primary/30 hover:ring-primary transition-all active:scale-95"
            type="button"
            aria-label="User Profile"
          >
            <img
              src={ASSETS.profileAvatar}
              alt="Farmer Ramesh Profile"
              className="w-full h-full object-cover"
            />
          </button>
        </div>
      </div>
    </header>
  );
};
