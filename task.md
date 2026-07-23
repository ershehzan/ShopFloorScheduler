# Phase 5: Enterprise Collaboration & Intelligence — Task Checklist

## Component 1: api.ts Bindings
- [x] Add `MachineShift` / `MachineShiftIn` / `MachineShiftOut` interfaces
- [x] Add `AssistantMessage` / `AssistantChatRequest` / `AssistantChatResponse` interfaces
- [x] Add shifts CRUD API functions (`getShifts`, `createShift`, `updateShift`, `deleteShift`, `getMachineShifts`)
- [x] Add assistant API functions (`chatWithAssistant`, `getAssistantPrompts`)

## Component 2: Shifts Management Page
- [x] Create `frontend/src/app/(dashboard)/shifts/page.tsx`
- [x] Create `frontend/src/app/(dashboard)/shifts/ShiftsClient.tsx`
  - [x] Table of all shift configurations
  - [x] Add Shift modal form
  - [x] Edit / Delete row actions
  - [x] Per-machine filter

## Component 3: AI Assistant Chat Page
- [x] Create `frontend/src/app/(dashboard)/assistant/page.tsx`
- [x] Create `frontend/src/app/(dashboard)/assistant/AssistantClient.tsx`
  - [x] Chat bubble layout (user right, assistant left)
  - [x] Markdown rendering for responses
  - [x] Suggested prompt chips
  - [x] Thinking / loading indicator
  - [x] Tool-call badge display
  - [x] Auto-scroll behavior

## Component 4: Sidebar Navigation
- [x] Add `Clock` and `MessageSquare` icons to Sidebar imports
- [x] Add `PHASE5_NAV_ITEMS` constant
- [x] Render Phase 5 nav section with emerald accent

## Finalize
- [x] Update `BRAIN.md` with Phase 5 changes
- [x] Create walkthrough
