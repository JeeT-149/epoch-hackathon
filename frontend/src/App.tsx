/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { ScreenType, Language, MandiItem } from './types';
import { Header } from './components/Header';
import { BottomNav } from './components/BottomNav';

import { HomeScreen } from './screens/HomeScreen';
import { WeatherScreen } from './screens/WeatherScreen';
import { MandiDetailsScreen } from './screens/MandiDetailsScreen';
import { AdviceScreen } from './screens/AdviceScreen';
import { MyCropsScreen } from './screens/MyCropsScreen';
import { MarketsScreen } from './screens/MarketsScreen';
import { ProfileScreen } from './screens/ProfileScreen';
import { EvidenceScreen } from './screens/EvidenceScreen';

import { HarvestCalculatorModal } from './components/modals/HarvestCalculatorModal';
import { RouteComparisonModal } from './components/modals/RouteComparisonModal';
import { VoiceModal } from './components/modals/VoiceModal';
import { LocationModal } from './components/modals/LocationModal';
import { NotificationsModal } from './components/modals/NotificationsModal';
import { MandiDetailPopupModal } from './components/modals/MandiDetailPopupModal';
import { TelegramModal } from './components/modals/TelegramModal';

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<ScreenType>('home');
  const [language, setLanguage] = useState<Language>(() => {
    const saved = window.localStorage.getItem('sell-smart-language');
    return saved === 'hi' || saved === 'mr' ? saved : 'en';
  });
  const [location, setLocation] = useState<string>('Nashik, Maharashtra • Dindori Taluka Block 4B');

  // Modals state
  const [isHarvestCalcOpen, setIsHarvestCalcOpen] = useState(false);
  const [isRouteModalOpen, setIsRouteModalOpen] = useState(false);
  const [isVoiceModalOpen, setIsVoiceModalOpen] = useState(false);
  const [isLocationModalOpen, setIsLocationModalOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isTelegramModalOpen, setIsTelegramModalOpen] = useState(false);
  const [selectedMandiForPopup, setSelectedMandiForPopup] = useState<MandiItem | null>(null);

  const changeLanguage = (next: Language) => {
    setLanguage(next);
    window.localStorage.setItem('sell-smart-language', next);
  };

  const handleVoiceQuery = (query: string) => {
    setCurrentScreen('chats');
  };

  const handleNavigate = (screen: ScreenType) => {
    setCurrentScreen(screen);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-surface font-body-md text-on-surface antialiased flex flex-col selection:bg-secondary-container selection:text-on-secondary-container">
      {/* Fixed Header */}
      <Header
        currentScreen={currentScreen}
        language={language}
        onLanguageChange={changeLanguage}
        onNavigate={handleNavigate}
        onOpenNotifications={() => setIsNotificationsOpen(true)}
        onOpenProfile={() => handleNavigate('profile')}
      />

      {/* Main Viewport Router */}
      <main className="flex-1 flex flex-col relative w-full">
        {currentScreen === 'home' && (
          <HomeScreen
            language={language}
            onNavigate={handleNavigate}
            onOpenVoiceModal={() => setIsVoiceModalOpen(true)}
            onOpenRouteModal={() => setIsRouteModalOpen(true)}
            onOpenLocationModal={() => setIsLocationModalOpen(true)}
            onOpenTelegramModal={() => setIsTelegramModalOpen(true)}
          />
        )}

        {currentScreen === 'weather' && (
          <WeatherScreen
            language={language}
            onOpenLocationModal={() => setIsLocationModalOpen(true)}
            onOpenBotDrawer={(initialQuery) => {
              handleNavigate('chats');
            }}
            onNavigateToCropDetail={(cropId) => {
              if (cropId === 'onion-alert') {
                handleNavigate('mandi-details');
              } else {
                handleNavigate('my-crops');
              }
            }}
          />
        )}

        {currentScreen === 'mandi-details' && (
          <MandiDetailsScreen
            language={language}
            onOpenHarvestCalculator={() => setIsHarvestCalcOpen(true)}
            onOpenMandiModal={(mandi) => setSelectedMandiForPopup(mandi)}
            onOpenTelegramModal={() => setIsTelegramModalOpen(true)}
            onNavigateHome={() => handleNavigate('home')}
          />
        )}

        {currentScreen === 'chats' && (
          <AdviceScreen
            language={language}
            onNavigate={handleNavigate}
          />
        )}

        {currentScreen === 'my-crops' && (
          <MyCropsScreen
            language={language}
            onNavigate={handleNavigate}
            onOpenHarvestCalculator={() => setIsHarvestCalcOpen(true)}
          />
        )}

        {currentScreen === 'markets' && (
          <MarketsScreen
            language={language}
            onNavigate={handleNavigate}
            onSelectMandi={(mandi) => setSelectedMandiForPopup(mandi)}
          />
        )}

        {currentScreen === 'evidence' && <EvidenceScreen language={language} />}

        {currentScreen === 'profile' && (
          <ProfileScreen
            language={language}
            onLanguageChange={(lang) => setLanguage(lang)}
            onOpenNotifications={() => setIsNotificationsOpen(true)}
            onOpenLocationModal={() => setIsLocationModalOpen(true)}
          />
        )}
      </main>

      {/* Fixed Bottom Navigation (hidden on stack screen if desired, or kept for convenient navigation) */}
      <BottomNav
        currentScreen={currentScreen}
        onNavigate={handleNavigate}
        language={language}
      />

      {/* Global Interactive Modals */}
      <HarvestCalculatorModal
        isOpen={isHarvestCalcOpen}
        onClose={() => setIsHarvestCalcOpen(false)}
        language={language}
      />

      <RouteComparisonModal
        isOpen={isRouteModalOpen}
        onClose={() => setIsRouteModalOpen(false)}
        language={language}
      />

      <VoiceModal
        isOpen={isVoiceModalOpen}
        onClose={() => setIsVoiceModalOpen(false)}
        onSelectQuery={handleVoiceQuery}
        language={language}
      />

      <LocationModal
        isOpen={isLocationModalOpen}
        onClose={() => setIsLocationModalOpen(false)}
        selectedLocation={location}
        onSelectLocation={(loc) => setLocation(loc)}
        language={language}
      />

      <NotificationsModal
        isOpen={isNotificationsOpen}
        onClose={() => setIsNotificationsOpen(false)}
        language={language}
      />

      <MandiDetailPopupModal
        mandi={selectedMandiForPopup}
        onClose={() => setSelectedMandiForPopup(null)}
        language={language}
        onOpenHarvestCalculator={() => setIsHarvestCalcOpen(true)}
      />

      <TelegramModal
        isOpen={isTelegramModalOpen}
        onClose={() => setIsTelegramModalOpen(false)}
        language={language}
      />
    </div>
  );
}
