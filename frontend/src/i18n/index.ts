/**
 * i18n/index.ts
 * Multi-language UI chrome strings for English (en), Marathi (mr), and Hindi (hi).
 * Translations for mr and hi are marked with needs_native_review.
 * Rule: Advice text always comes directly from the backend.
 */

export type SupportedLanguage = 'en' | 'mr' | 'hi';

export interface UIStrings {
  appName: string;
  tagline: string;
  demoRibbon: string;
  simulatedNotice: string;
  syntheticNotice: string;
  placeholderNotice: string;
  send: string;
  recording: string;
  tapToSpeak: string;
  tapToStop: string;
  voiceProcessing: string;
  voiceConfirmTitle: string;
  yesConfirm: string;
  editClarify: string;
  voiceUnavailableFallback: string;
  inputPlaceholder: string;
  connecting: string;
  errorTitle: string;
  errorMessage: string;
  retry: string;
  statusAccept: string;
  statusSwitch: string;
  statusWait: string;
  statusSellNow: string;
  statusNoAdvice: string;
  typicalGainMedian: string;
  rangeLabel: string;
  confidenceLabel: string;
  mandiComparison: string;
  transportCost: string;
  netReturn: string;
  triggerCondition: string;
  regretReceiptTitle: string;
  actualPriceReceived: string;
  counterfactualComparison: string;
  regretAmount: string;
  daysHeld: string;
  modalPriceDisclaimer: string;
  activePlanMonitoring: string;
  planActiveSubtitle: string;
  recordOutcome: string;
  recordOutcomeTitle: string;
  mandiLabel: string;
  pricePerQuintal: string;
  quantityQuintals: string;
  submitOutcome: string;
  tabChat: string;
  tabInsights: string;
  tabBacktest: string;
  calibrationPassport: string;
  shockRadar: string;
  needsNativeReview?: boolean;
}

export const translations: Record<SupportedLanguage, UIStrings> = {
  en: {
    appName: 'SHETBHAV',
    tagline: 'Fair-Price Guardian & Decision Engine',
    demoRibbon: 'DEMO DATA — MOCK',
    simulatedNotice: 'SIMULATED OUTCOME',
    syntheticNotice: 'Demo Price & Scenario Data Active',
    placeholderNotice: 'Uncalibrated parameters present — Demo only',
    send: 'Send',
    recording: 'Listening... Tap to stop',
    tapToSpeak: 'Hold or tap to speak your crop, mandi or offer',
    tapToStop: 'Stop recording',
    voiceProcessing: 'Transcribing speech...',
    voiceConfirmTitle: 'Confirm what we heard',
    yesConfirm: 'Yes, Get Advice',
    editClarify: 'Edit / Clarify',
    voiceUnavailableFallback: 'Voice recognition unavailable. Please type your query.',
    inputPlaceholder: 'e.g., Sold 50q onion at ₹1800 or trader offering ₹1500 in Nashik...',
    connecting: 'Analyzing market opportunities...',
    errorTitle: 'Communication Error',
    errorMessage: 'Unable to reach the decision service. Please check your connection.',
    retry: 'Retry Request',
    statusAccept: 'Accept Current Offer',
    statusSwitch: 'Switch Mandi Today',
    statusWait: 'Wait with Trigger Condition',
    statusSellNow: 'Sell Now at Nearest Mandi',
    statusNoAdvice: 'No Confident Advice Possible',
    typicalGainMedian: 'Typical (median) net gain',
    rangeLabel: 'Likely range',
    confidenceLabel: 'Confidence level',
    mandiComparison: 'Alternative Mandis Compared',
    transportCost: 'Estimated transport cost',
    netReturn: 'Net projected return',
    triggerCondition: 'Trigger Rule / Exit Condition',
    regretReceiptTitle: 'Decision Regret Receipt',
    actualPriceReceived: 'Actual Realised Price',
    counterfactualComparison: 'Best Available Alternative Outcome',
    regretAmount: 'Outcome Delta (vs Best Alternate)',
    daysHeld: 'Days Held in Storage',
    modalPriceDisclaimer: 'Modal price is a market-level reference, not a guaranteed realisation price.',
    activePlanMonitoring: 'Trigger Engine Active (Polling every 20s)',
    planActiveSubtitle: 'Monitoring mandi price triggers in real time',
    recordOutcome: 'Log Actual Sale',
    recordOutcomeTitle: 'Log Final Mandi Sale Outcome',
    mandiLabel: 'Mandi Name',
    pricePerQuintal: 'Actual Sale Price (₹/q)',
    quantityQuintals: 'Quantity (Quintals)',
    submitOutcome: 'Calculate Regret Receipt',
    tabChat: 'Guardian Advisor',
    tabInsights: 'Radar & Risk',
    tabBacktest: 'Validation & Passport',
    calibrationPassport: 'Calibration Passport',
    shockRadar: 'Policy-Shock Radar',
  },
  mr: {
    // needs_native_review: Marathi localized UI chrome strings
    needsNativeReview: true,
    appName: 'सेलस्मार्ट (SellSmart)',
    tagline: 'वाजवी भाव मार्गदर्शक आणि निर्णय यंत्रणा',
    demoRibbon: 'डेमो डेटा — मॉक (नमुना)',
    simulatedNotice: 'सिम्युलेटेड निकाल',
    syntheticNotice: 'सिंथेटिक भाव आणि परिस्थिती डेटा सक्रिय',
    placeholderNotice: 'असमायोजित निकष उपस्थित — केवळ नमुन्यासाठी',
    send: 'पाठवा',
    recording: 'ऐकत आहे... थांबवण्यासाठी दाबा',
    tapToSpeak: 'तुमचे पीक, बाजार किंवा ऑफर सांगण्यासाठी बोला',
    tapToStop: 'रेकॉर्डिंग थांबवा',
    voiceProcessing: 'आवाज रूपांतरित होत आहे...',
    voiceConfirmTitle: 'नोंद तपासून घ्या',
    yesConfirm: 'होय, सल्ला द्या',
    editClarify: 'बदला / स्पष्ट करा',
    voiceUnavailableFallback: 'व्हॉइस सेवा उपलब्ध नाही. कृपया लिहून पाठवा.',
    inputPlaceholder: 'उदा. नाशिकमध्ये कांदा ₹१५०० चा भाव मिळतोय, काय करू?',
    connecting: 'बाजार संधींचे विश्लेषण सुरू आहे...',
    errorTitle: 'संपर्क त्रुटी',
    errorMessage: 'सर्व्हरशी संपर्क होऊ शकला नाही. कृपया पुन्हा प्रयत्न करा.',
    retry: 'पुन्हा प्रयत्न करा',
    statusAccept: 'सध्याची ऑफर स्वीकारा',
    statusSwitch: 'दुसऱ्या बाजार समितीत (मंडीत) विक्री करा',
    statusWait: 'थांबा आणि भाव लक्ष ठेवा',
    statusSellNow: 'जवळच्या बाजार समितीत लगेच विका',
    statusNoAdvice: 'निश्चित सल्ला उपलब्ध नाही',
    typicalGainMedian: 'अपेक्षित (मध्यक) निव्वळ नफा',
    rangeLabel: 'संभाव्य मर्यादा',
    confidenceLabel: 'विश्वासार्हता स्तर',
    mandiComparison: 'इतर बाजार समित्यांची तुलना',
    transportCost: 'अंदाजे वाहतूक खर्च',
    netReturn: 'निव्वळ अपेक्षित परतावा',
    triggerCondition: 'लक्ष्य किंमत / विक्री अट',
    regretReceiptTitle: 'निर्णय पडताळणी पावती',
    actualPriceReceived: 'प्रत्यक्ष मिळालेला भाव',
    counterfactualComparison: 'सर्वोत्तम पर्यायी निकाल',
    regretAmount: 'परताव्यातील फरक',
    daysHeld: 'साठवणुकीचे दिवस',
    modalPriceDisclaimer: 'मोडल भाव हा बाजार-स्तरीय संदर्भ आहे, ही हमी दिलेली किंमत नाही.',
    activePlanMonitoring: 'ट्रिगर इंजिन सक्रिय (दर २० सेकंदांनी तपासणी)',
    planActiveSubtitle: 'किंमत बदलांवर थेट लक्ष ठेवले जात आहे',
    recordOutcome: 'प्रत्यक्ष विक्री नोंदवा',
    recordOutcomeTitle: 'अंतिम विक्री नोंद करा',
    mandiLabel: 'बाजार समिती',
    pricePerQuintal: 'प्रत्यक्ष भाव (₹/क्विंटल)',
    quantityQuintals: 'प्रमाण (क्विंटल)',
    submitOutcome: 'पावती मिळवा',
    tabChat: 'सल्लागार',
    tabInsights: 'बाजार जोखीम रडार',
    tabBacktest: 'प्रमाणीकरण व पासपोर्ट',
    calibrationPassport: 'कॅलिब्रेशन पासपोर्ट',
    shockRadar: 'धोरण-धक्का रडार',
  },
  hi: {
    // needs_native_review: Hindi localized UI chrome strings
    needsNativeReview: true,
    appName: 'सेलस्मार्ट (SellSmart)',
    tagline: 'उचित मूल्य रक्षक और निर्णय प्रणाली',
    demoRibbon: 'डेमो डेटा — मॉक (नमूना)',
    simulatedNotice: 'सिम्युलेटेड परिणाम',
    syntheticNotice: 'सिंथेटिक भाव और परिदृश्य डेटा सक्रिय',
    placeholderNotice: 'असमायोजित पैरामीटर — केवल डेमो हेतु',
    send: 'भेजें',
    recording: 'सुन रहे हैं... रोकने के लिए टैप करें',
    tapToSpeak: 'अपनी फसल, मंडी या व्यापारी का भाव बोलने के लिए टैप करें',
    tapToStop: 'रिकॉर्डिंग बंद करें',
    voiceProcessing: 'आवाज़ संसाधित हो रही है...',
    voiceConfirmTitle: 'क्या यह विवरण सही है?',
    yesConfirm: 'हाँ, सलाह दें',
    editClarify: 'सुधारें / स्पष्ट करें',
    voiceUnavailableFallback: 'वॉयस इनपुट अनुपलब्ध है। कृपया लिखकर भेजें।',
    inputPlaceholder: 'उदा. नासिक में 50 क्विंटल प्याज पर ₹1500 मिल रहा है, क्या बेचूं?',
    connecting: 'बाजार के अवसरों का विश्लेषण हो रहा है...',
    errorTitle: 'कनेक्शन त्रुटि',
    errorMessage: 'सेवा से संपर्क नहीं हो पाया। कृपया पुनः प्रयास करें।',
    retry: 'पुनः प्रयास करें',
    statusAccept: 'वर्तमान व्यापारी ऑफर स्वीकारें',
    statusSwitch: 'आज ही दूसरी मंडी में बेचें',
    statusWait: 'शर्त के साथ रुकें (ट्रिगर)',
    statusSellNow: 'निकटतम मंडी में तुरंत बेचें',
    statusNoAdvice: 'विश्वसनीय सलाह उपलब्ध नहीं',
    typicalGainMedian: 'विशिष्ट (मध्यक) शुद्ध लाभ',
    rangeLabel: 'संभावित दायरा',
    confidenceLabel: 'विश्वसनीयता स्तर',
    mandiComparison: 'वैकल्पिक मंडियों की तुलना',
    transportCost: 'अनुमानित परिवहन लागत',
    netReturn: 'अनुमानित शुद्ध प्राप्ति',
    triggerCondition: 'निर्गम शर्त / मूल्य ट्रिगर',
    regretReceiptTitle: 'निर्णय पश्चाताप रसीद',
    actualPriceReceived: 'वास्तविक प्राप्त भाव',
    counterfactualComparison: 'सर्वोत्तम वैकल्पिक अवसर',
    regretAmount: 'शुद्ध प्राप्ति अंतर',
    daysHeld: 'भंडारण में दिन',
    modalPriceDisclaimer: 'मॉडल मूल्य एक बाजार-स्तरीय संदर्भ है, यह गारंटीशुदा प्राप्ति मूल्य नहीं है।',
    activePlanMonitoring: 'ट्रिगर इंजन सक्रिय (हर 20 सेकंड में अपडेट)',
    planActiveSubtitle: 'मंडी के भाव परिवर्तनों पर निरंतर निगरानी',
    recordOutcome: 'वास्तविक बिक्री दर्ज करें',
    recordOutcomeTitle: 'अंतिम बिक्री विवरण दर्ज करें',
    mandiLabel: 'मंडी का नाम',
    pricePerQuintal: 'प्राप्त भाव (₹/क्विंटल)',
    quantityQuintals: 'मात्रा (क्विंटल)',
    submitOutcome: 'रसीद देखें',
    tabChat: 'संरक्षक सलाहकार',
    tabInsights: 'जोखिम रडार',
    tabBacktest: 'सत्यापन व पासपोर्ट',
    calibrationPassport: 'कैलिब्रेशन पासपोर्ट',
    shockRadar: 'नीति-झटका रडार',
  },
};
