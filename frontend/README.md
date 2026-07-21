# Nyaya AI Next.js Frontend

This directory contains the production-ready Next.js dark/light theme frontend codebase for the Nyaya AI Indian Legal Intelligence platform, ported from the HTML mockup templates.

---

## 🛠️ Tech Stack & Key Choices

1. **Framework**: Next.js 14 App Router with TypeScript.
2. **Styling**: Tailwind CSS + Custom CSS Variables matching the morning snow and dark mahogany palettes.
3. **Icons**: Lucide React.
4. **Session Persistence & Route Protection**: Cookies and server-side `middleware.ts` to execute redirects on `/dashboard`, `/chat`, and `/scan` routes before rendering, eliminating any client-side layout flashing.
5. **API Client**: Axios instance in `src/lib/api.ts` with request interceptors to automatically read the auth token cookie and attach it as an `Authorization: Bearer <token>` header.

---

## 🚀 How to Run Locally

### 1. Install Node Dependencies
From the `frontend/` directory, install all packages:
```bash
npm install
```

### 2. Configure Environment Variables (Optional)
By default, the application connects to the backend at `http://localhost:8000`. To change this, create a `.env.local` file inside the `frontend/` folder:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Start Development Server
```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser to view the application.

---

## 📁 Code Structure

* **`src/middleware.ts`**: Runs server-side to guard protected dashboard, scanner, and chat routes.
* **`src/lib/api.ts`**: The Axios HTTP client utility.
* **`src/components/Header.tsx`**: Universal top navigation with theme toggle, dynamic avatar, and logout functions.
* **`src/app/page.tsx`**: Static landing page.
* **`src/app/signin/page.tsx`**: User login and sign-up with email inputs mapped to backend `username` requirements.
* **`src/app/dashboard/page.tsx`**: Portfolios dashboard showing live database stats, ingestion scan history table, RAG chat history, and PDF download actions.
* **`src/app/chat/page.tsx`**: Research chat interface displaying chatbot panels and active cited authority cards on the left column.
* **`src/app/scan/page.tsx`**: Workstation scanning interface with drag-and-drop file uploading, scan polling status, detailed risk card navigators, statutory explanations, and supporting landmark judicial precedents.
