import posthog from 'posthog-js';

const POSTHOG_TOKEN = process.env.REACT_APP_POSTHOG_PROJECT_TOKEN;

// 1. Point this by default to your new custom Cloudflare worker domain
const POSTHOG_HOST = process.env.REACT_APP_POSTHOG_HOST || 'assets.bhavanaapp.com';

/** Initialize PostHog once (idempotent). Call at app root. */
export function initPostHog(): void {
  if (!POSTHOG_TOKEN) {
    if (process.env.NODE_ENV === 'development') {
      console.warn('[PostHog] No REACT_APP_POSTHOG_PROJECT_TOKEN set — skipping init');
    }
    return;
  }
  if (typeof window === 'undefined') return; // SSR guard

  posthog.init(POSTHOG_TOKEN, {
    api_host: POSTHOG_HOST,
    
    // 2. Add this so PostHog admin tools can still talk to your frontend
    ui_host: 'https://us.posthog.com', // Use 'https://eu.posthog.com' if using EU residency
    
    person_profiles: 'identified_only', // respect privacy
    capture_pageview: true,
    capture_pageleave: true,
    loaded: () => {
      if (process.env.NODE_ENV === 'development') {
        console.log('[PostHog] Initialized via Reverse Proxy');
      }
    },
  });
}

/** Convenience wrapper to capture events. */
export function captureEvent(
  event: string,
  properties?: Record<string, string | number | boolean | undefined>,
): void {
  if (!POSTHOG_TOKEN) return;
  try {
    posthog.capture(event, properties);
  } catch (e) {
    console.error('[PostHog] capture error', e);
  }
}