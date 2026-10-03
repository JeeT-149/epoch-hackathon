/**
 * api/adapter.ts
 * Single adapter holding all endpoint paths, field mappings, and network transports.
 * Changes to contracts or backend endpoints require only editing this file.
 * Env support: VITE_USE_MOCKS / EXPO_PUBLIC_USE_MOCKS (defaults to true).
 */

import {
  ChatReply,
  ChatReplySchema,
  RegretReceipt,
  RegretReceiptSchema,
  ShockStatus,
  ShockStatusSchema,
  CalibrationPassport,
  CalibrationPassportSchema,
  BacktestSummary,
  BacktestSummarySchema,
  NotificationEvent,
  NotificationEventSchema,
} from '../contracts/schemas';

import {
  mockAcceptOffer,
  mockSwitchMarketNow,
  mockWaitWithTrigger,
  mockSellNowNearest,
  mockNoConfidentAdvice,
  mockClarification,
  mockVoiceConfirm,
  mockRegretReceipt,
  mockShockStatus,
  mockCalibrationPassport,
  mockBacktestSummary,
  mockNotifications,
} from '../mocks/fixtures';

// Configuration from environment with robust defaults
const getEnvVar = (key: string, fallback: string): string => {
  try {
    const metaEnv = (import.meta as any)?.env;
    if (metaEnv) {
      if (metaEnv[key]) return metaEnv[key];
      if (metaEnv[`VITE_${key}`]) return metaEnv[`VITE_${key}`];
    }
  } catch (e) {
    // Ignore in non-vite contexts
  }
  return fallback;
};

export const CONFIG = {
  USE_MOCKS: getEnvVar('USE_MOCKS', 'true') === 'true',
  LLM_BASE_URL: getEnvVar('LLM_BASE_URL', 'http://localhost:8000/api/llm'),
  ML_BASE_URL: getEnvVar('ML_BASE_URL', 'http://localhost:8000/api/ml'),
  TIMEOUT_MS: 10000,
};

// Centralized endpoint definitions
export const ENDPOINTS = {
  // LLM Layer endpoints
  CHAT: '/chat',
  VOICE: '/voice',
  OUTCOME: '/outcome',
  NOTIFICATIONS: '/notifications',
  HEALTH: '/health',

  // ML Service read-only GET endpoints
  META: '/meta',
  CALIBRATION: '/calibration',
  SHOCK_STATUS: '/shock-status',
  BACKTEST_SUMMARY: '/backtest-summary',
};

// Safe schema parser that logs a non-blocking dev warning on mismatch and never crashes
function safeParse<T>(schema: { safeParse: (data: unknown) => { success: boolean; data?: T; error?: any } }, data: unknown, fallback: T): T {
  const result = schema.safeParse(data);
  if (!result.success) {
    console.warn('[Contract Validation Warning] Schema mismatch, falling back gracefully:', result.error);
    return (data as T) || fallback;
  }
  return result.data as T;
}

// Timeout fetch wrapper
async function fetchWithTimeout(url: string, options: RequestInit = {}): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), CONFIG.TIMEOUT_MS);
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(id);
    return response;
  } catch (error) {
    clearTimeout(id);
    throw error;
  }
}

export interface ChatRequestPayload {
  session_id: string;
  message: string;
  language?: string;
  source?: 'text' | 'voice';
  confirm?: boolean;
}

export interface VoiceRequestPayload {
  session_id: string;
  audio_base64?: string;
  audio_uri?: string;
  mime_type?: string;
}

export interface OutcomeRequestPayload {
  session_id: string;
  crop: string;
  mandi_id: string;
  actual_price: number;
  quantity_q: number;
  sale_date?: string;
}

export interface CropAnalysis {
  crop_name?: string;
  ripeness?: string;
  damage?: string;
  sell_timing?: string;
  price_range?: string;
  confidence?: string;
  notes?: string;
  source?: string;
}

export class ApiAdapter {
  private useMocks: boolean = CONFIG.USE_MOCKS;

  constructor(forceMocks?: boolean) {
    if (forceMocks !== undefined) {
      this.useMocks = forceMocks;
    }
  }

  setMockMode(enabled: boolean) {
    this.useMocks = enabled;
  }

  isMockMode(): boolean {
    return this.useMocks;
  }

  // --- LLM LAYER CALLS ---

  async sendChat(payload: ChatRequestPayload): Promise<ChatReply> {
    if (this.useMocks) {
      await new Promise((r) => setTimeout(r, 400));
      const msg = payload.message.toLowerCase();

      if (payload.confirm) {
        return mockWaitWithTrigger;
      }
      if (msg.includes('switch') || msg.includes('pimpalgaon')) {
        return mockSwitchMarketNow;
      }
      if (msg.includes('wait') || msg.includes('hold')) {
        return mockWaitWithTrigger;
      }
      if (msg.includes('sell now') || msg.includes('nearest') || msg.includes('nashik road')) {
        return mockSellNowNearest;
      }
      if (msg.includes('shock') || msg.includes('uncertain')) {
        return mockNoConfidentAdvice;
      }
      if (msg.includes('where') || msg.includes('which') || msg.includes('clarify')) {
        return mockClarification;
      }
      if (payload.source === 'voice') {
        return mockVoiceConfirm;
      }
      return mockAcceptOffer;
    }

    try {
      const response = await fetchWithTimeout(`${CONFIG.LLM_BASE_URL}${ENDPOINTS.CHAT}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`HTTP Error ${response.status}`);
      }

      const json = await response.json();
      return safeParse(ChatReplySchema, json, mockAcceptOffer);
    } catch (err) {
      console.error('[API Error in sendChat]:', err);
      throw err;
    }
  }

  async sendVoice(payload: VoiceRequestPayload): Promise<{ transcript: string; session_id: string }> {
    if (this.useMocks) {
      await new Promise((r) => setTimeout(r, 600));
      return {
        session_id: payload.session_id,
        transcript: 'I have 60 quintals of onion near Pimpalgaon, local trader is offering 1900 rupees.',
      };
    }

    try {
      const response = await fetchWithTimeout(`${CONFIG.LLM_BASE_URL}${ENDPOINTS.VOICE}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`Voice HTTP Error ${response.status}`);
      }

      return await response.json();
    } catch (err) {
      console.error('[API Error in sendVoice]:', err);
      throw err;
    }
  }

  async recordOutcome(payload: OutcomeRequestPayload): Promise<RegretReceipt> {
    if (this.useMocks) {
      await new Promise((r) => setTimeout(r, 350));
      return {
        ...mockRegretReceipt,
        crop: payload.crop,
        actual_price_received: payload.actual_price,
        actual_net_return: Math.round(payload.actual_price - 135),
        regret_per_q: Math.round((payload.actual_price - 135) - mockRegretReceipt.counterfactual_net_return),
      };
    }

    try {
      const response = await fetchWithTimeout(`${CONFIG.LLM_BASE_URL}${ENDPOINTS.OUTCOME}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`Outcome HTTP Error ${response.status}`);
      }

      const json = await response.json();
      return safeParse(RegretReceiptSchema, json, mockRegretReceipt);
    } catch (err) {
      console.error('[API Error in recordOutcome]:', err);
      throw err;
    }
  }

  async getNotifications(sessionId: string): Promise<NotificationEvent[]> {
    if (this.useMocks) {
      return mockNotifications;
    }

    try {
      const response = await fetchWithTimeout(`${CONFIG.LLM_BASE_URL}${ENDPOINTS.NOTIFICATIONS}?session_id=${encodeURIComponent(sessionId)}`);
      if (!response.ok) throw new Error(`Notifications HTTP Error ${response.status}`);
      const json = await response.json();
      return Array.isArray(json) ? json.map((item) => safeParse(NotificationEventSchema, item, item)) : [];
    } catch (err) {
      console.warn('[API Warning in getNotifications]:', err);
      return [];
    }
  }

  // --- ML SERVICE READ-ONLY GET CALLS ---

  async getShockStatus(crop: string = 'Onion', mandiId: string = 'mh_nashik_lasalgaon'): Promise<ShockStatus> {
    if (this.useMocks) {
      return mockShockStatus;
    }

    try {
      const response = await fetchWithTimeout(`${CONFIG.ML_BASE_URL}${ENDPOINTS.SHOCK_STATUS}?crop=${crop}&mandi_id=${mandiId}`);
      if (!response.ok) throw new Error(`Shock status HTTP Error ${response.status}`);
      const json = await response.json();
      return safeParse(ShockStatusSchema, json, mockShockStatus);
    } catch (err) {
      console.warn('[API Warning in getShockStatus]:', err);
      return mockShockStatus;
    }
  }

  async getCalibrationPassport(crop: string = 'Onion', mandiId: string = 'mh_nashik_lasalgaon'): Promise<CalibrationPassport> {
    if (this.useMocks) {
      return mockCalibrationPassport;
    }

    try {
      const response = await fetchWithTimeout(`${CONFIG.ML_BASE_URL}${ENDPOINTS.CALIBRATION}?crop=${crop}&mandi_id=${mandiId}`);
      if (!response.ok) throw new Error(`Calibration HTTP Error ${response.status}`);
      const json = await response.json();
      return safeParse(CalibrationPassportSchema, json, mockCalibrationPassport);
    } catch (err) {
      console.warn('[API Warning in getCalibrationPassport]:', err);
      return mockCalibrationPassport;
    }
  }

  async getBacktestSummary(crop: string = 'Onion'): Promise<BacktestSummary> {
    if (this.useMocks) {
      return mockBacktestSummary;
    }

    try {
      const response = await fetchWithTimeout(`${CONFIG.ML_BASE_URL}${ENDPOINTS.BACKTEST_SUMMARY}?crop=${crop}`);
      if (!response.ok) throw new Error(`Backtest HTTP Error ${response.status}`);
      const json = await response.json();
      return safeParse(BacktestSummarySchema, json, mockBacktestSummary);
    } catch (err) {
      console.warn('[API Warning in getBacktestSummary]:', err);
      return mockBacktestSummary;
    }
  }

  async analyzeCropImage(file: File, crop: string, language: string): Promise<CropAnalysis> {
    const imageData = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result));
      reader.onerror = () => reject(new Error('Could not read image'));
      reader.readAsDataURL(file);
    });
    if (this.useMocks) {
      await new Promise((resolve) => setTimeout(resolve, 700));
      const localized = language === 'mr'
        ? { onion: { crop_name: 'कांदा', ripeness: 'विक्रीसाठी योग्य', damage: 'मोठे नुकसान दिसत नाही', sell_timing: '१–२ दिवसांत विका', price_range: '₹२,१००–₹२,४०० / क्विंटल', notes: 'फोटोवरून प्राथमिक अंदाज. प्रत्यक्ष गुणवत्ता तपासा.' }, tomato: { crop_name: 'टोमॅटो', ripeness: 'अर्धपिकलेला', damage: 'काही मऊ डाग', sell_timing: 'लवकर विका', price_range: '₹१,५००–₹१,९०० / क्विंटल', notes: 'वाहतुकीपूर्वी खराब फळे वेगळी करा.' }, soybean: { crop_name: 'सोयाबीन', ripeness: 'काढणीसाठी जवळ', damage: 'मोठे नुकसान दिसत नाही', sell_timing: 'हवामान कोरडे असताना विका', price_range: '₹४,४००–₹४,८०० / क्विंटल', notes: 'दाण्याची आर्द्रता प्रत्यक्ष तपासा.' } }
        : language === 'hi'
          ? { onion: { crop_name: 'प्याज़', ripeness: 'बेचने के लिए ठीक', damage: 'बड़ा नुकसान नहीं दिखता', sell_timing: '१–२ दिन में बेचें', price_range: '₹२,१००–₹२,४०० / क्विंटल', notes: 'फोटो पर आधारित शुरुआती अनुमान। असली गुणवत्ता जांचें।' }, tomato: { crop_name: 'टमाटर', ripeness: 'आधा पका', damage: 'कुछ नरम दाग', sell_timing: 'जल्दी बेचें', price_range: '₹१,५००–₹१,९०० / क्विंटल', notes: 'ढुलाई से पहले खराब फल अलग करें।' }, soybean: { crop_name: 'सोयाबीन', ripeness: 'कटाई के करीब', damage: 'बड़ा नुकसान नहीं दिखता', sell_timing: 'सूखे मौसम में बेचें', price_range: '₹४,४००–₹४,८०० / क्विंटल', notes: 'दाने की नमी जरूर जांचें।' } }
          : { onion: { crop_name: 'Onion', ripeness: 'Ready to sell', damage: 'No major damage visible', sell_timing: 'Sell within 1–2 days', price_range: '₹2,100–₹2,400 / quintal', notes: 'Initial photo-based estimate. Confirm quality in person.' }, tomato: { crop_name: 'Tomato', ripeness: 'Partly ripe', damage: 'Some soft spots', sell_timing: 'Sell soon', price_range: '₹1,500–₹1,900 / quintal', notes: 'Separate damaged fruit before transport.' }, soybean: { crop_name: 'Soybean', ripeness: 'Nearly ready for harvest', damage: 'No major damage visible', sell_timing: 'Sell during a dry window', price_range: '₹4,400–₹4,800 / quintal', notes: 'Check grain moisture before sale.' } };
      return { ...(localized[crop as keyof typeof localized] || localized.onion), confidence: 'MEDIUM', source: 'Price and crop fixture' };
    }
    const response = await fetch('/api/analyze-crop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_data: imageData, crop, language }),
    });
    if (!response.ok) {
      let detail = '';
      try {
        const body = await response.text();
        try { detail = JSON.parse(body)?.detail || body; } catch { detail = body; }
      } catch { /* non-JSON proxy error */ }
      throw new Error(detail || `Crop analysis HTTP Error ${response.status}`);
    }
    return response.json();
  }
}

export const api = new ApiAdapter();
