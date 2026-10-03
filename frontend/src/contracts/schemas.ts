/**
 * contracts/schemas.ts
 * Zod validation schemas for LLM Layer & ML Service API contracts.
 * Tolerates extra fields (.passthrough()), renders what is valid, and never crashes.
 */
import { z } from 'zod';

export const DecisionStatusEnum = z.enum([
  'ACCEPT_OFFER',
  'SWITCH_MARKET_NOW',
  'WAIT_WITH_TRIGGER',
  'SELL_NOW_NEAREST',
  'NO_CONFIDENT_ADVICE',
]);

export type DecisionStatus = z.infer<typeof DecisionStatusEnum> | string;

export const MetaSchema = z.object({
  ml_mode: z.enum(['mock', 'live', 'hybrid']).default('mock'),
  price_source: z.enum(['real', 'synthetic']).default('synthetic'),
  demo_ready: z.boolean().default(false),
  simulation_notice: z.string().nullable().optional(),
  headline_gain_claim: z.string().nullable().optional(),
  disclaimers: z.array(z.string()).default([]).optional(),
  mock: z.boolean().default(true),
}).passthrough();

export type Meta = z.infer<typeof MetaSchema>;

export const SellingOptionSchema = z.object({
  mandi_id: z.string(),
  mandi_name: z.string().optional(),
  selling_day_offset: z.number().default(0),
  target_date: z.string().optional(),
  projected_modal_price: z.number(),
  transport_cost_per_q: z.number().default(0),
  net_return_per_q: z.number(),
  distance_km: z.number().optional(),
  is_nearest: z.boolean().optional(),
}).passthrough();

export type SellingOption = z.infer<typeof SellingOptionSchema>;

export const TriggerDetailsSchema = z.object({
  trigger_price: z.number(),
  exit_deadline_days: z.number(),
  condition_description: z.string(),
  mandi_id: z.string().optional(),
  target_mandi_name: z.string().optional(),
}).passthrough();

export type TriggerDetails = z.infer<typeof TriggerDetailsSchema>;

export const ClarificationSchema = z.object({
  question: z.string(),
  quick_replies: z.array(z.string()),
  field_needed: z.string().optional(),
}).passthrough();

export type Clarification = z.infer<typeof ClarificationSchema>;

export const ConfirmParseSchema = z.object({
  transcript: z.string(),
  crop: z.string().optional(),
  mandi: z.string().optional(),
  offer_per_q: z.number().nullable().optional(),
  quantity_q: z.number().nullable().optional(),
  cash_deadline_days: z.number().nullable().optional(),
  confirm_message: z.string(),
}).passthrough();

export type ConfirmParse = z.infer<typeof ConfirmParseSchema>;

export const ChatReplySchema = z.object({
  session_id: z.string(),
  text: z.string(),
  language: z.enum(['en', 'mr', 'hi']).default('en').optional(),
  status: DecisionStatusEnum.or(z.string()).optional(),
  recommendation_title: z.string().optional(),
  typical_gain_median: z.number().nullable().optional(),
  likely_range_min: z.number().nullable().optional(),
  likely_range_max: z.number().nullable().optional(),
  confidence_label: z.enum(['HIGH', 'MEDIUM', 'LOW', 'NONE']).default('MEDIUM').optional(),
  confidence_score: z.number().min(0).max(1).default(0.5).optional(),
  modal_price_footer: z.string().default('Modal price is a market-level reference, not a guaranteed realisation price.').optional(),
  options_comparison: z.array(SellingOptionSchema).optional(),
  trigger_details: TriggerDetailsSchema.nullable().optional(),
  clarification: ClarificationSchema.nullable().optional(),
  confirm_parse: ConfirmParseSchema.nullable().optional(),
  meta: MetaSchema.default({
    ml_mode: 'mock',
    price_source: 'synthetic',
    demo_ready: false,
    mock: true,
  }).optional(),
  mock: z.boolean().default(true).optional(),
}).passthrough();

export type ChatReply = z.infer<typeof ChatReplySchema>;

export const RegretReceiptSchema = z.object({
  crop: z.string(),
  mandi_id: z.string(),
  decision_date: z.string(),
  sell_date: z.string(),
  recommended_action: z.string(),
  actual_price_received: z.number(),
  actual_net_return: z.number(),
  counterfactual_price: z.number(),
  counterfactual_net_return: z.number(),
  regret_per_q: z.number(),
  days_held: z.number(),
  is_placeholder: z.boolean().default(false),
  is_simulated: z.boolean().default(true),
  note: z.string().default('Regret is difference between actual outcome and best available alternative at decision time.'),
  mock: z.boolean().default(true),
}).passthrough();

export type RegretReceipt = z.infer<typeof RegretReceiptSchema>;

export const ShockStatusSchema = z.object({
  crop: z.string(),
  mandi_id: z.string(),
  is_shock_active: z.boolean(),
  z_score: z.number(),
  z_threshold: z.number().default(3.0),
  message: z.string(),
  lookback_days: z.number().default(30),
  events_detected: z.number().default(0),
  dq_score: z.number().min(0).max(1).nullable().optional(),
  n_obs_last_90d: z.number().nullable().optional(),
  last_obs_days_ago: z.number().nullable().optional(),
  model_coverage: z.number().nullable().optional(),
  backtest_mae: z.number().nullable().optional(),
  gate_allowed: z.boolean().nullable().optional(),
  gate_reason: z.string().nullable().optional(),
  data_source: z.string().nullable().optional(),
  mock: z.boolean().default(true),
}).passthrough();

export type ShockStatus = z.infer<typeof ShockStatusSchema>;

export const CalibrationPassportSchema = z.object({
  crop: z.string(),
  mandi_id: z.string(),
  horizon_days: z.number(),
  n_test_samples: z.number(),
  generated_at: z.string(),
  calibration: z.record(z.object({
    target_coverage: z.number().optional(),
    empirical_fraction_below: z.number().optional(),
    calibration_error: z.number().optional(),
    empirical_coverage: z.number().optional(),
    mean_interval_width: z.number().optional(),
    q_hat: z.number().optional(),
  })),
  tolerance: z.number().optional(),
  data_source: z.string().optional(),
  mock: z.boolean().default(true),
}).passthrough();

export type CalibrationPassport = z.infer<typeof CalibrationPassportSchema>;

export const BacktestSummarySchema = z.object({
  crop: z.string(),
  evaluated_period: z.string(),
  total_scenarios: z.number(),
  guardian_win_rate_pct: z.number(),
  median_net_gain_inr: z.number(),
  mean_net_gain_inr: z.number(),
  loss_rate_pct: z.number(),
  where_we_lose_money: z.string(),
  baseline_comparisons: z.array(z.object({
    baseline_name: z.string(),
    mean_gain_inr: z.number(),
    win_rate_pct: z.number(),
  })),
  headline_result: z.string().nullable().optional(),
  real_prices: z.boolean().optional(),
  confidence_interval: z.object({ low: z.number(), high: z.number() }).nullable().optional(),
  crisis_replay: z.array(z.object({
    label: z.string(),
    with_radar: z.number().optional(),
    without_radar: z.number().optional(),
    is_synthetic: z.boolean().optional(),
  }).passthrough()).optional(),
  loss_scenarios: z.array(z.object({
    scenario: z.string(),
    cause: z.string(),
    loss_inr: z.number().optional(),
  }).passthrough()).optional(),
  labels: z.array(z.string()).optional(),
  mock: z.boolean().default(true),
}).passthrough();

export type BacktestSummary = z.infer<typeof BacktestSummarySchema>;

export const NotificationEventSchema = z.object({
  id: z.string(),
  event_type: z.enum(['price_drop', 'price_rise', 'shock', 'timeout', 'sell_signal']),
  crop: z.string(),
  mandi_id: z.string(),
  event_date: z.string(),
  price: z.number(),
  reference_price: z.number(),
  pct_change: z.number(),
  message: z.string(),
  action_required: z.string().optional(),
  mock: z.boolean().default(true),
}).passthrough();

export type NotificationEvent = z.infer<typeof NotificationEventSchema>;
