# Rukmer GPT – Frontend (Next.js)

This folder will contain the **web app** that all tenants use to:

- Sign up / log in
- Upload images and videos
- Browse their media library
- View a media item (image/video) in a viewer
- Chat with Rukmer GPT about their uploaded content

The frontend talks ONLY to the backend API (FastAPI), sending a JWT that includes:
- `tenant_id`
- `user_id`

It never talks directly to the database or storage.

---

## Tech Stack (planned)

- **Framework:** Next.js (React)
- **Language:** TypeScript
- **Styling:** (to be decided: Tailwind CSS / CSS Modules / etc.)
- **State:** React Query or simple hooks for now
- **Auth:** JWT from backend

---

## Planned Folder Structure

When we scaffold the Next.js app, we expect something like:

```text
frontend/
  app/                # Next.js App Router pages
    page.tsx         # Main landing/dashboard
  components/         # Reusable UI components
    MediaGrid.tsx
    MediaCard.tsx
    MediaViewer.tsx
    GPTChatPanel.tsx
  lib/                # API client helpers, utils
  public/             # Static assets
  package.json
  tsconfig.json
  next.config.mjs
```
