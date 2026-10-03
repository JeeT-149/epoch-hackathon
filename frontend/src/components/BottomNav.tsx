import React from 'react';
import { ScreenType, Language } from '../types';

interface BottomNavProps {
  currentScreen: ScreenType;
  onNavigate: (screen: ScreenType) => void;
  language: Language;
}

export const BottomNav: React.FC<BottomNavProps> = ({
  currentScreen,
  onNavigate,
  language,
}) => {
  const tabs = [
    {
      id: 'home' as ScreenType,
      label: language === 'mr' ? 'मुख्य' : language === 'hi' ? 'होम' : 'Home',
      icon: 'home',
    },
    {
      id: 'chats' as ScreenType,
      label: language === 'mr' ? 'सल्ला' : language === 'hi' ? 'सलाह' : 'Advice',
      icon: 'chat_bubble',
    },
    {
      id: 'my-crops' as ScreenType,
      label: language === 'mr' ? 'पिके' : language === 'hi' ? 'फसल' : 'Crops',
      icon: 'agriculture',
    },
    {
      id: 'markets' as ScreenType,
      label: language === 'mr' ? 'बाजार' : language === 'hi' ? 'मंडी' : 'Markets',
      icon: 'storefront',
    },
    {
      id: 'evidence' as ScreenType,
      label: language === 'mr' ? 'पुरावा' : language === 'hi' ? 'भरोसा' : 'Evidence',
      icon: 'fact_check',
    },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 pb-safe bg-surface border-t border-surface-container-high shadow-[0_-2px_8px_rgba(31,42,31,0.06)]">
      <div className="flex justify-between items-center h-16 px-1 max-w-xl mx-auto">
        {tabs.map((tab) => {
          const isActive = currentScreen === tab.id || (tab.id === 'markets' && currentScreen === 'mandi-details');

          return (
            <button
              key={tab.id}
              onClick={() => onNavigate(tab.id)}
              className={`flex-1 flex flex-col items-center justify-center min-h-[48px] py-1 transition-all duration-150 ${
                isActive
                  ? 'text-primary font-bold scale-105'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
              type="button"
            >
              <div className="relative">
                <span
                  className="material-symbols-outlined text-[23px]"
                  style={isActive ? { fontVariationSettings: "'FILL' 1" } : undefined}
                >
                  {tab.icon}
                </span>
                {tab.id === 'evidence' && (
                  <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-error ring-1 ring-surface animate-ping"></span>
                )}
              </div>
              <span className={`text-[11px] leading-tight mt-0.5 truncate tracking-tight ${isActive ? 'font-bold text-primary' : 'font-medium'}`}>
                {tab.label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};
