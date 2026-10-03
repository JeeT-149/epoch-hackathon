import React, { useState } from 'react';
import { Language } from '../../types';

interface VoiceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectQuery: (query: string) => void;
  language: Language;
}

export const VoiceModal: React.FC<VoiceModalProps> = ({
  isOpen,
  onClose,
  onSelectQuery,
  language,
}) => {
  const [isRecording, setIsRecording] = useState(false);

  if (!isOpen) return null;

  const handleMicTap = () => {
    setIsRecording(true);
    setTimeout(() => {
      setIsRecording(false);
      onSelectQuery('I have 60 quintals of onion near Pimpalgaon, local trader is offering ₹1,900');
      onClose();
    }, 1800);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <div className="bg-surface-container-lowest rounded-3xl p-6 w-full max-w-sm border border-outline-variant shadow-2xl text-center">
        <div className="flex justify-between items-center mb-6">
          <span className="text-xs font-bold text-outline uppercase tracking-wider">Voice Guardian</span>
          <button onClick={onClose} className="p-1 rounded-full hover:bg-surface-container">
            <span className="material-symbols-outlined text-outline">close</span>
          </button>
        </div>

        <h3 className="font-bold text-lg text-on-surface mb-2">
          {language === 'mr' ? 'बोला, आम्ही ऐकत आहोत...' : 'Speak your crop, mandi or offer'}
        </h3>
        <p className="text-xs text-on-surface-variant mb-8 leading-relaxed">
          {isRecording
            ? (language === 'mr' ? 'ऐकत आहे... कृपया बोला' : 'Listening... Processing speech')
            : (language === 'mr' ? 'माईक बटण दाबा आणि विचारा' : 'Tap the microphone to speak')}
        </p>

        {/* Large Accessible Microphone Button (>= 48px touch target) */}
        <div className="flex justify-center mb-6">
          <button
            onClick={handleMicTap}
            className={`w-20 h-20 rounded-full flex items-center justify-center text-white shadow-xl transition-transform active:scale-95 ${
              isRecording ? 'bg-error animate-pulse' : 'bg-primary hover:bg-primary-container'
            }`}
          >
            <span className="material-symbols-outlined text-4xl">mic</span>
          </button>
        </div>

        <div className="text-[11px] text-outline italic">
          Try saying: &quot;Trader offering ₹1,900 for onion in Pimpalgaon&quot;
        </div>
      </div>
    </div>
  );
};
