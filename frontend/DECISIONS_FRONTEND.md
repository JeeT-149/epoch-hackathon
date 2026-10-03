# Frontend Decisions & Notes

This document records architectural, design, and implementation decisions made for the SellSmart frontend application.

## UI Design & Shell Integration (Phase 2)
- **UI Architecture**: Implemented the custom multi-screen mobile-first design provided by user using React 18, Vite, and Tailwind CSS v4 (`@tailwindcss/vite`).
- **Design Tokens & Theme**: Incorporated `@layer base` CSS variables with Material 3 palette (`--color-surface: #f0fdec`, `--color-primary: #50604d`, etc.), Material Symbols font, and responsive spacing tokens in `src/index.css`.
- **Navigation & Screens**:
  - `src/App.tsx`: Central application state, persistent "DEMO DATA — MOCK" ribbon, fixed header, modal orchestrator, and bottom navigation.
  - Screen routes: `home`, `weather`, `mandi-details`, `chats`, `my-crops`, `markets`, `profile`.
  - Global Modals: `HarvestCalculatorModal`, `RouteComparisonModal`, `VoiceModal`, `LocationModal`, `NotificationsModal`, `MandiDetailPopupModal`, `TelegramModal`.
- **API & Mock Engine**:
  - Centralized in `src/api/adapter.ts`, proxying `/api/llm` and `/api/ml` in Vite dev server to protect against CORS.
  - Complete Zod contracts in `src/contracts/schemas.ts` and rich fixtures in `src/mocks/fixtures.ts`.
- **Verification**:
  - Production build (`tsc && vite build`) passes with 0 errors.
  - PowerShell check confirms 0 changes outside `frontend/`.
