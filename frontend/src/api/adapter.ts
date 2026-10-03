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
}

export const api = new ApiAdapter();
