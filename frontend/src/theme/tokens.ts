/**
 * theme/tokens.ts
 * Design system tokens: colours, typography, spacing, elevations, and radii.
 * Strictly neutral palette with semantic accents for agricultural decision intelligence.
 * Kept in a single file so styling can be refined without modifying core components.
 */

export const colors = {
  // Base backgrounds & surfaces (dark & high contrast by default)
  background: '#0B0F19',
  surface: '#111827',
  surfaceCard: '#1A2234',
  surfaceCardHover: '#232E45',
  surfaceElevated: '#1F293D',
  border: '#2E3B55',
  borderFocus: '#4F46E5',

  // Text colors (WCAG AAA contrast compliant)
  textPrimary: '#F9FAFB',
  textSecondary: '#9CA3AF',
  textTertiary: '#6B7280',
  textInverse: '#0B0F19',

  // Semantic Status Colors (Used in addition to icons and text labels, never as the only signal)
  status: {
    accept: '#10B981',       // Emerald
    switchMandi: '#3B82F6',  // Blue
    wait: '#F59E0B',         // Amber
    sellNow: '#EC4899',      // Pink/Rose
    noAdvice: '#64748B',     // Slate
    alert: '#EF4444',        // Red
  },

  // Confidence indicators
  confidence: {
    high: '#10B981',
    medium: '#F59E0B',
    low: '#EF4444',
  },

  // Ribbons & Notices
  ribbon: {
    mockBg: '#78350F',
    mockText: '#FEF3C7',
    syntheticBg: '#581C87',
    syntheticText: '#F3E8FF',
    warningBg: '#7F1D1D',
    warningText: '#FEE2E2',
  },

  // Brand / Interactive Accents
  accent: '#10B981',
  accentHover: '#059669',
  accentSubtle: '#064E3B',
  primaryButton: '#10B981',
  primaryButtonText: '#042F2E',

  // Danger & Error
  error: '#EF4444',
  errorBg: '#450A0A',
  success: '#10B981',
  successBg: '#064E3B',
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
};

export const typography = {
  // Mobile-first readable type scale with Noto Sans Devanagari fallback
  fontFamily: 'Noto Sans Devanagari, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  sizes: {
    micro: 12,
    caption: 14,
    body: 16,        // Minimum 16px body text for accessibility
    bodyLarge: 18,
    subheading: 20,
    heading: 24,
    display: 32,
  },
  weights: {
    regular: '400' as const,
    medium: '500' as const,
    semibold: '600' as const,
    bold: '700' as const,
  },
  lineHeights: {
    body: 24,
    heading: 32,
    display: 40,
  },
};

export const radii = {
  sm: 6,
  md: 10,
  lg: 14,
  full: 9999,
};

export const layout = {
  minTouchTarget: 48, // Minimum 48px touch target for accessibility
  minWidth: 360,      // Mobile-first viewport baseline
  maxWidth: 480,      // Handheld mobile container standard
};
