export type Language = 'en' | 'mr' | 'hi';

export type ScreenType = 'home' | 'weather' | 'mandi-details' | 'chats' | 'my-crops' | 'markets' | 'evidence' | 'profile';

export interface WeatherDay {
  day: string;
  dayLabel: { en: string; mr: string; hi?: string };
  tempMax: number;
  tempMin: number;
  rainMm: number;
  condition: string;
  conditionIcon: string;
  rainChance: number;
  humidity: number;
  windSpeed: number;
  windDirection: string;
  soilMoisture: number;
  soilStatus: string;
  active?: boolean;
}

export interface CropAlert {
  id: string;
  name: { en: string; mr: string; hi?: string };
  variety: string;
  plot: string;
  stage: { en: string; mr: string; hi?: string };
  statusTag: { en: string; mr: string; hi?: string };
  statusType: 'urgent' | 'alert' | 'favorable' | 'caution';
  description: { en: string; mr: string; hi?: string };
  actionType: 'dispatch' | 'spray' | 'info';
  actionLabel: { en: string; mr: string; hi?: string };
  actionValue: { en: string; mr: string; hi?: string };
  imageUrl: string;
}

export interface MandiItem {
  id: string;
  rank: number;
  name: string;
  distanceKm: number;
  location: string;
  netTakeHome: number;
  modalPrice: number;
  freightCost: number;
  arrivalVolume: number;
  arrivalTrend: 'Moderate flow' | 'Steady' | 'Slow trading' | 'Heavy rush';
  arrivalTrendType: 'positive' | 'steady' | 'negative';
  isHighestNet?: boolean;
}

export interface TrendingCrop {
  id: string;
  name: { en: string; mr: string; hi?: string };
  variety: string;
  modalPrice: number;
  deltaPercent: number;
  trend: 'up' | 'down';
  imageUrl: string;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'bot';
  text: string;
  timestamp: string;
  chips?: string[];
  actionLink?: {
    label: string;
    screen: ScreenType;
  };
}
