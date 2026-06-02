import posthog from 'posthog-js';

const POSTHOG_TOKEN = process.env.REACT_APP_POSTHOG_PROJECT_TOKEN;
const POSTHOG_HOST = process.env.REACT_APP_POSTHOG_HOST || 'https://us.i.posthog.com';

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
    person_profiles: 'identified_only', // respect privacy
    capture_pageview: true,
    capture_pageleave: true,
    loaded: () => {
      if (process.env.NODE_ENV === 'development') {
        console.log('[PostHog] Initialized');
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