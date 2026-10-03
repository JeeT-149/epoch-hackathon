/**
 * hooks/useTranslation.ts
 * React context and hook for multi-language UI chrome strings.
 * Defaults to backend reply language when received.
 */
import React, { createContext, useContext, useState, useMemo } from 'react';
import { SupportedLanguage, UIStrings, translations } from '../i18n';

interface TranslationContextType {
  language: SupportedLanguage;
  setLanguage: (lang: SupportedLanguage) => void;
  t: UIStrings;
}

const TranslationContext = createContext<TranslationContextType>({
  language: 'en',
  setLanguage: () => {},
  t: translations.en,
});

export const TranslationProvider: React.FC<{ children: React.ReactNode; initialLanguage?: SupportedLanguage }> = ({
  children,
  initialLanguage = 'en',
}) => {
  const [language, setLanguage] = useState<SupportedLanguage>(initialLanguage);

  const t = useMemo(() => translations[language] || translations.en, [language]);

  return (
    <TranslationContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </TranslationContext.Provider>
  );
};

export const useTranslation = () => useContext(TranslationContext);
