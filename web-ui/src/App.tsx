import React, { useState, useEffect, useRef } from 'react';
import { initPostHog, captureEvent } from './posthog';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.REACT_APP_SUPABASE_URL!,
  process.env.REACT_APP_SUPABASE_ANON_KEY!
);

/* ─── Brand tokens ──────────────────────────────────────────────────── */
const css = `
  @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400&family=DM+Sans:wght@300;400;500&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --void:      #100e1a;
    --deep:      #1c1830;
    --dusk:      #2e2850;
    --iris:      #7b6fd0;
    --lavender:  #a89fe8;
    --breath:    #4db896;
    --dawn:      #e8b87a;
    --mist:      #c0bde8;
    --ghost:     rgba(192,189,232,0.38);
    --border:    rgba(160,148,240,0.18);
    --font-display: 'Cormorant Garamond', Georgia, serif;
    --font-ui:      'DM Sans', system-ui, sans-serif;
    --ease-breath:  cubic-bezier(0.45, 0.05, 0.55, 0.95);
  }

  html, body, #root {
    height: 100%;
    background: var(--void);
    color: var(--mist);
    font-family: var(--font-ui);
    font-weight: 300;
    -webkit-font-smoothing: antialiased;
  }

  /* ── Full-viewport atmospheric backdrop ── */
  .backdrop {
    position: fixed;
    inset: 0;
    background: var(--void);
    z-index: 0;
  }

  /* ── Layout ── */
  .shell {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 2rem 1.25rem 3rem;
    position: relative;
    z-index: 1;
  }

  /* ── Ambient orbs ── */
  .orb {
    position: fixed;
    border-radius: 50%;
    pointer-events: none;
    filter: blur(90px);
    opacity: 0.5;
    animation: drift 14s var(--ease-breath) infinite alternate;
    z-index: 0;
  }
  .orb-1 { width: 55vw; height: 55vw; max-width: 700px; max-height: 700px; background: #4a3aaa; top: -15vw; right: -10vw; animation-delay: 0s; }
  .orb-2 { width: 45vw; height: 45vw; max-width: 580px; max-height: 580px; background: #1a6e58; bottom: -10vw; left: -10vw; animation-delay: -5s; }
  .orb-3 { width: 30vw; height: 30vw; max-width: 380px; max-height: 380px; background: #8a3060; top: 50%; right: 6%; animation-delay: -9s; }

  @keyframes drift {
    from { transform: translate(0, 0) scale(1); }
    to   { transform: translate(16px, 24px) scale(1.06); }
  }

  /* ── Card ── */
  .card {
    position: relative;
    z-index: 1;
    width: 100%;
    max-width: 420px;
    background: rgba(28, 24, 48, 0.72);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border: 0.5px solid var(--border);
    border-radius: 24px;
    padding: 2.5rem 2rem 2rem;
  }

  /* ── Crossfade wrapper ── */
  .fade-wrap {
    transition: opacity 0.9s var(--ease-breath);
  }
  .fade-wrap.hidden {
    opacity: 0;
    pointer-events: none;
  }

  /* ── Header ── */
  .tod {
    text-align: center;
    font-size: 10px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--ghost);
    margin-bottom: 0.5rem;
  }

  .brand-title {
    font-family: var(--font-display);
    font-size: 34px;
    font-weight: 300;
    letter-spacing: 0.02em;
    color: rgba(235, 232, 255, 0.92);
    text-align: center;
    line-height: 1.15;
    margin-bottom: 0.3rem;
  }

  .tagline {
    text-align: center;
    font-size: 12px;
    letter-spacing: 0.06em;
    color: var(--ghost);
    margin-bottom: 2rem;
  }

  /* ── Loading state ── */
  .loading-msg {
    text-align: center;
    font-size: 12px;
    letter-spacing: 0.08em;
    color: var(--ghost);
    margin-bottom: 1.5rem;
    animation: fade-pulse 2s ease-in-out infinite;
  }

  @keyframes fade-pulse {
    0%, 100% { opacity: 0.4; }
    50%       { opacity: 1; }
  }

  /* ── Pill groups ── */
  .pill-group { margin-bottom: 1.1rem; }

  .pill-label {
    font-size: 9px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: rgba(160, 148, 240, 0.45);
    margin-bottom: 8px;
  }

  .pills { display: flex; gap: 7px; flex-wrap: wrap; }

  .pill {
    padding: 7px 16px;
    border-radius: 30px;
    font-size: 13px;
    font-family: var(--font-ui);
    font-weight: 300;
    cursor: pointer;
    border: 0.5px solid rgba(255,255,255,0.1);
    background: rgba(255,255,255,0.04);
    color: rgba(192,189,232,0.45);
    transition: all 0.18s ease-out;
    user-select: none;
    letter-spacing: 0.02em;
  }

  .pill:hover {
    background: rgba(255,255,255,0.09);
    color: rgba(192,189,232,0.8);
    border-color: rgba(160,148,240,0.3);
  }

  .pill.active {
    background: rgba(123,111,208,0.2);
    border-color: rgba(123,111,208,0.55);
    color: rgba(200,190,255,0.95);
  }

  .pill:disabled, .pill.disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }

  /* ── Unavailable notice ── */
  .unavailable {
    font-size: 12px;
    color: rgba(232,184,122,0.7);
    letter-spacing: 0.04em;
    margin-top: 0.75rem;
    text-align: center;
  }

  /* ── Divider ── */
  .divider {
    height: 0.5px;
    background: var(--border);
    margin: 1.5rem 0;
  }

  /* ── Breathing ring ── */
  .ring-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin-bottom: 1.5rem;
  }

  .ring {
    width: 110px;
    height: 110px;
    border-radius: 50%;
    border: 1px solid rgba(160,148,240,0.3);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    position: relative;
    transition: border-color 0.3s;
    margin-bottom: 0.75rem;
  }

  .ring::before {
    content: '';
    position: absolute;
    width: 88px; height: 88px;
    border-radius: 50%;
    background: rgba(100,80,180,0.12);
    transition: background 0.3s;
  }

  .ring:hover { border-color: rgba(160,148,240,0.6); }
  .ring:hover::before { background: rgba(100,80,180,0.22); }

  .ring.playing {
    border-color: rgba(160,148,240,0.65);
    animation: breathe-ring 4s var(--ease-breath) infinite;
  }

  .ring.playing::before {
    animation: breathe-fill 4s var(--ease-breath) infinite;
  }

  @keyframes breathe-ring {
    0%,100% { transform: scale(1);    border-color: rgba(140,120,220,0.45); }
    50%      { transform: scale(1.07); border-color: rgba(140,120,220,0.85); }
  }

  @keyframes breathe-fill {
    0%,100% { transform: scale(1);    background: rgba(100,80,180,0.12); }
    50%      { transform: scale(1.06); background: rgba(100,80,180,0.28); }
  }

  .ring-icon {
    position: relative;
    z-index: 1;
    font-size: 22px;
    color: rgba(200,190,255,0.8);
    transition: color 0.2s;
    line-height: 1;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .ring:hover .ring-icon { color: rgba(220,215,255,1); }

  .ring-icon svg { width: 22px; height: 22px; }

  .session-label {
    font-size: 12px;
    letter-spacing: 0.04em;
    color: var(--ghost);
    text-align: center;
    min-height: 16px;
    transition: color 0.4s;
  }

  .session-label.active { color: rgba(168,159,232,0.85); }

  /* ── Progress ── */
  .progress-area { margin-bottom: 1.25rem; }

  .progress-track {
    height: 2px;
    background: rgba(255,255,255,0.08);
    border-radius: 2px;
    cursor: pointer;
    margin-bottom: 7px;
    position: relative;
  }

  .progress-fill {
    height: 100%;
    border-radius: 2px;
    background: linear-gradient(90deg, var(--iris), var(--breath));
    width: 0%;
    transition: width 0.7s linear;
    pointer-events: none;
  }

  .time-labels {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    font-family: 'DM Mono', 'Courier New', monospace;
    color: rgba(192,189,232,0.25);
    letter-spacing: 0.04em;
  }

  /* ── Bottom row: play ring on left, volume sliders toward center-right ── */
  .bottom-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  /* ── Left side: play ring ── */
  .bottom-left {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }

  .ring-actions {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  /* ── Right side: stacked volume sliders ── */
  .vol-stack {
    display: flex;
    flex-direction: column;
    gap: 4px;
    flex: 1;
    max-width: 160px;
    margin-left: 12px;
    margin-top: -8px;
  }

  .icon-btn {
    background: none;
    border: none;
    cursor: pointer;
    color: rgba(192,189,232,0.3);
    padding: 7px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.18s;
    flex-shrink: 0;
  }

  .icon-btn:hover:not(:disabled) {
    color: rgba(192,189,232,0.75);
    background: rgba(255,255,255,0.07);
  }

  .icon-btn:disabled { opacity: 0.2; cursor: not-allowed; }

  .icon-btn svg { width: 18px; height: 18px; }

  .vol-wrap {
    display: flex;
    align-items: center;
    gap: 7px;
  }

  .vol-wrap svg { width: 15px; height: 15px; color: rgba(192,189,232,0.28); flex-shrink: 0; }

  input[type=range].vol-slider {
    -webkit-appearance: none;
    appearance: none;
    height: 2px;
    border-radius: 2px;
    background: rgba(255,255,255,0.1);
    outline: none;
    flex: 1;
    cursor: pointer;
  }

  input[type=range].vol-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 11px; height: 11px;
    border-radius: 50%;
    background: rgba(168,159,232,0.8);
    cursor: pointer;
  }

  /* ── Volume label for dual sliders ── */
  .vol-label {
    font-size: 8px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: rgba(192,189,232,0.2);
    flex-shrink: 0;
    width: 22px;
    text-align: center;
  }

  /* ── Download row below progress bar ── */
  .download-row {
    display: flex;
    justify-content: center;
    margin-bottom: 0.75rem;
  }

  /* ── Variation hint ── */
  .var-hint {
    text-align: center;
    font-size: 11px;
    letter-spacing: 0.04em;
    color: rgba(192,189,232,0.2);
    margin-top: 1.25rem;
  }

  .var-hint button {
    background: none;
    border: none;
    cursor: pointer;
    color: rgba(160,148,240,0.55);
    font-size: 11px;
    font-family: var(--font-ui);
    letter-spacing: 0.04em;
    text-decoration: underline;
    text-underline-offset: 3px;
    padding: 0;
    transition: color 0.18s;
  }

  .var-hint button:hover { color: rgba(168,159,232,0.85); }

  audio { display: none; }

  .error-msg {
    text-align: center;
    font-size: 12px;
    color: rgba(232,184,122,0.7);
    margin-top: 0.5rem;
    letter-spacing: 0.03em;
  }

  /* ════════════════════════════════════════════════════════════════════
     FEEDBACK SCREEN
  ════════════════════════════════════════════════════════════════════ */

  /* Outer container that sits on top of the player via absolute positioning */
  .feedback-wrap {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 2rem 1.25rem 3rem;
    z-index: 2;
    transition: opacity 1.1s var(--ease-breath);
    pointer-events: none;
    opacity: 0;
  }

  .feedback-wrap.visible {
    opacity: 1;
    pointer-events: auto;
  }

  .feedback-card {
    position: relative;
    z-index: 1;
    width: 100%;
    max-width: 420px;
    background: rgba(28, 24, 48, 0.72);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border: 0.5px solid var(--border);
    border-radius: 24px;
    padding: 2.8rem 2rem 2.4rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0;
  }

  /* Soft checkmark glyph shown after session ends */
  .session-end-glyph {
    font-size: 28px;
    margin-bottom: 1.2rem;
    opacity: 0.7;
    animation: glyph-in 1.2s var(--ease-breath) forwards;
  }

  @keyframes glyph-in {
    from { opacity: 0; transform: scale(0.7); }
    to   { opacity: 0.7; transform: scale(1); }
  }

  .feedback-title {
    font-family: var(--font-display);
    font-size: 28px;
    font-weight: 300;
    color: rgba(235, 232, 255, 0.9);
    text-align: center;
    letter-spacing: 0.02em;
    margin-bottom: 0.35rem;
  }

  .feedback-subtitle {
    font-size: 12px;
    letter-spacing: 0.07em;
    color: var(--ghost);
    text-align: center;
    margin-bottom: 2.2rem;
  }

  /* ── Mood options ── */
  .mood-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    width: 100%;
    margin-bottom: 1.8rem;
  }

  .mood-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    padding: 16px 10px 14px;
    border-radius: 18px;
    border: 0.5px solid rgba(255,255,255,0.08);
    background: rgba(255,255,255,0.03);
    cursor: pointer;
    transition: all 0.22s var(--ease-breath);
    user-select: none;
    position: relative;
    overflow: hidden;
  }

  .mood-btn::before {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: 18px;
    opacity: 0;
    transition: opacity 0.22s ease;
  }

  /* Per-mood accent colours on hover/active */
  .mood-btn[data-mood="flowing"]::before  { background: radial-gradient(ellipse at 50% 120%, rgba(77,184,150,0.18), transparent 70%); }
  .mood-btn[data-mood="clear"]::before    { background: radial-gradient(ellipse at 50% 120%, rgba(232,184,122,0.18), transparent 70%); }
  .mood-btn[data-mood="drifting"]::before { background: radial-gradient(ellipse at 50% 120%, rgba(168,159,232,0.15), transparent 70%); }
  .mood-btn[data-mood="restless"]::before { background: radial-gradient(ellipse at 50% 120%, rgba(220,100,80,0.16), transparent 70%); }

  .mood-btn:hover::before, .mood-btn.selected::before { opacity: 1; }

  .mood-btn:hover {
    border-color: rgba(160,148,240,0.25);
    background: rgba(255,255,255,0.06);
    transform: translateY(-1px);
  }

  .mood-btn.selected {
    border-color: rgba(160,148,240,0.5);
    background: rgba(123,111,208,0.12);
    transform: translateY(-1px);
  }

  .mood-emoji {
    font-size: 26px;
    line-height: 1;
    position: relative;
    z-index: 1;
  }

  .mood-label {
    font-size: 12px;
    letter-spacing: 0.06em;
    color: rgba(192,189,232,0.55);
    font-weight: 400;
    position: relative;
    z-index: 1;
    transition: color 0.2s;
  }

  .mood-btn:hover .mood-label,
  .mood-btn.selected .mood-label {
    color: rgba(200,190,255,0.9);
  }

  /* ── Text expansion ── */
  .nota-reveal {
    width: 100%;
    overflow: hidden;
    max-height: 0;
    opacity: 0;
    transition: max-height 0.55s var(--ease-breath), opacity 0.5s ease;
  }

  .nota-reveal.open {
    max-height: 220px;
    opacity: 1;
  }

  .nota-trigger {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 11px;
    letter-spacing: 0.07em;
    color: rgba(160,148,240,0.5);
    font-family: var(--font-ui);
    text-decoration: underline;
    text-underline-offset: 3px;
    padding: 0;
    margin-bottom: 1.4rem;
    display: block;
    width: 100%;
    text-align: center;
    transition: color 0.18s;
  }

  .nota-trigger:hover { color: rgba(168,159,232,0.85); }

  .nota-box {
    width: 100%;
    background: rgba(255,255,255,0.03);
    border: 0.5px solid rgba(160,148,240,0.2);
    border-radius: 14px;
    padding: 14px 16px;
    font-size: 13px;
    font-family: var(--font-ui);
    font-weight: 300;
    color: rgba(192,189,232,0.85);
    resize: none;
    outline: none;
    letter-spacing: 0.02em;
    line-height: 1.6;
    transition: border-color 0.2s;
    min-height: 90px;
    margin-bottom: 10px;
  }

  .nota-box::placeholder { color: rgba(192,189,232,0.22); }
  .nota-box:focus { border-color: rgba(160,148,240,0.45); }

  /* ── Submit button ── */
  .feedback-submit {
    width: 100%;
    padding: 12px 0;
    border-radius: 30px;
    border: 0.5px solid rgba(123,111,208,0.45);
    background: rgba(123,111,208,0.14);
    color: rgba(200,190,255,0.9);
    font-size: 12px;
    font-family: var(--font-ui);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    cursor: pointer;
    transition: all 0.2s ease-out;
  }

  .feedback-submit:hover {
    background: rgba(123,111,208,0.26);
    border-color: rgba(123,111,208,0.7);
  }

  /* ── Skip link ── */
  .feedback-skip {
    margin-top: 1.4rem;
    background: none;
    border: none;
    cursor: pointer;
    font-size: 11px;
    letter-spacing: 0.06em;
    color: rgba(192,189,232,0.2);
    font-family: var(--font-ui);
    transition: color 0.18s;
  }

  .feedback-skip:hover { color: rgba(192,189,232,0.5); }

  /* ── Thank-you state ── */
  .thankyou-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    animation: glyph-in 0.8s var(--ease-breath) forwards;
  }

  .thankyou-glyph { font-size: 32px; opacity: 0.75; }

  .thankyou-title {
    font-family: var(--font-display);
    font-size: 26px;
    font-weight: 300;
    color: rgba(235,232,255,0.88);
    text-align: center;
    letter-spacing: 0.02em;
    margin-top: 0.4rem;
  }

  .thankyou-sub {
    font-size: 12px;
    letter-spacing: 0.06em;
    color: var(--ghost);
    text-align: center;
    margin-bottom: 1.8rem;
  }

  .new-session-btn {
    padding: 11px 32px;
    border-radius: 30px;
    border: 0.5px solid rgba(123,111,208,0.4);
    background: rgba(123,111,208,0.12);
    color: rgba(200,190,255,0.85);
    font-size: 12px;
    font-family: var(--font-ui);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    cursor: pointer;
    transition: all 0.2s ease-out;
  }

  .new-session-btn:hover {
    background: rgba(123,111,208,0.24);
    border-color: rgba(123,111,208,0.65);
  }

  /* ════════════════════════════════════════════════════════════════════
     PWA INSTALL BANNER
  ════════════════════════════════════════════════════════════════════ */
  .install-banner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 10px 14px;
    margin-bottom: 1.25rem;
    border-radius: 16px;
    background: rgba(123,111,208,0.12);
    border: 0.5px solid rgba(123,111,208,0.3);
    animation: glyph-in 0.6s var(--ease-breath) forwards;
  }

  .install-banner-text {
    font-size: 11px;
    letter-spacing: 0.04em;
    color: rgba(200,190,255,0.8);
    line-height: 1.4;
  }

  .install-banner-btn {
    flex-shrink: 0;
    padding: 7px 16px;
    border-radius: 20px;
    border: 0.5px solid rgba(123,111,208,0.5);
    background: rgba(123,111,208,0.2);
    color: rgba(220,215,255,0.95);
    font-size: 11px;
    font-family: var(--font-ui);
    letter-spacing: 0.06em;
    cursor: pointer;
    transition: all 0.18s ease-out;
    white-space: nowrap;
  }

  .install-banner-btn:hover {
    background: rgba(123,111,208,0.35);
    border-color: rgba(123,111,208,0.7);
  }

  .install-banner-close {
    flex-shrink: 0;
    background: none;
    border: none;
    cursor: pointer;
    color: rgba(192,189,232,0.25);
    font-size: 16px;
    padding: 2px 4px;
    transition: color 0.18s;
    line-height: 1;
  }

  .install-banner-close:hover {
    color: rgba(192,189,232,0.6);
  }
`;

/* ─── Types ─────────────────────────────────────────────────────────── */
interface MeditationLogEntry {
  duration: string;
  level: string | null;
  variation: number | null;
  model: string | null;
  date_generated: string;
  music: string;
  guided: boolean;
}

interface MeditationLog {
  meditations: MeditationLogEntry[];
}

interface BackgroundLogEntry {
  duration: string;
  date_generated: string;
  music: string;
  source_file: string;
}

interface BackgroundLog {
  backgrounds: BackgroundLogEntry[];
}

type AppScreen = 'player' | 'feedback' | 'thankyou';

/* ─── Constants ─────────────────────────────────────────────────────── */
const R2_BUCKET_URL = "https://pub-e5092eb6363d42ce8ac557dbecc589f0.r2.dev";

const MOOD_OPTIONS = [
  { id: 'flowing',  emoji: '🌊', label: 'En flujo' },
  { id: 'clear',    emoji: '☀️', label: 'Despejado' },
  { id: 'drifting', emoji: '🌫️', label: 'A la deriva' },
  { id: 'restless', emoji: '🔥', label: 'Inquieto' },
] as const;

type MoodId = typeof MOOD_OPTIONS[number]['id'];

/* ─── Helpers ───────────────────────────────────────────────────────── */
function parseDurationMinutes(duration: string): number {
  const match = duration.match(/(\d+)/);
  return match ? parseInt(match[1], 10) : 0;
}

function buildR2Url(entry: MeditationLogEntry): string {
  const durationNum = parseDurationMinutes(entry.duration);
  if (entry.guided) {
    // Voice track is always the pure voice from meditations/silence/
    return `${R2_BUCKET_URL}/meditations/silence/${durationNum}_${entry.level}_${entry.variation}.opus`;
  } else {
    return `${R2_BUCKET_URL}/meditations/mute/${durationNum}_${entry.music}.opus`;
  }
}

/**
 * Check if a background audio file exists for the given duration and music type,
 * based on the backgrounds_log.json registry.
 */
function isBackgroundAvailable(
  backgroundsLog: BackgroundLog | null,
  duration: string,
  music: string
): boolean {
  if (!backgroundsLog) return false;
  const durationNum = parseDurationMinutes(duration);
  return backgroundsLog.backgrounds.some(
    b => parseDurationMinutes(b.duration) === durationNum && b.music === music
  );
}

/**
 * Build the URL for the background audio track.
 * Files are stored in sounds/backgrounds/ and named like 5_nature.opus
 */
function buildBackgroundUrl(entry: MeditationLogEntry): string {
  const durationNum = parseDurationMinutes(entry.duration);
  return `${R2_BUCKET_URL}/sounds/backgrounds/${durationNum}_${entry.music}.opus`;
}

function formatDuration(duration: string): string {
  const num = parseDurationMinutes(duration);
  return `${num} min`;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s < 10 ? '0' : ''}${s}`;
}

function getTimeOfDay(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Buenos días';
  if (h < 19) return 'Buenas tardes';
  return 'Buenas noches';
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function musicDisplayName(key: string): string {
  const labels: Record<string, string> = {
    nature: 'Naturaleza',
    silence: 'Silencio',
    binaural: 'Binaural',
  };
  return labels[key] ?? capitalize(key);
}

/* ─── SVG icon components ───────────────────────────────────────────── */
const IconPlay = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="5 3 19 12 5 21 5 3" fill="currentColor" stroke="none" />
  </svg>
);

const IconPause = () => (
  <svg viewBox="0 0 24 24" fill="currentColor">
    <rect x="6" y="4" width="4" height="16" rx="1" />
    <rect x="14" y="4" width="4" height="16" rx="1" />
  </svg>
);

const IconDownload = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="7 10 12 15 17 10" />
    <line x1="12" y1="15" x2="12" y2="3" />
  </svg>
);

const IconVolume = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
    <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
  </svg>
);

const IconLeaf = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M11 20A7 7 0 0 1 9.8 6.9C15.5 4.9 17 3.5 19 2c1 2 2 4.5 2 8 0 5.5-4.78 10-10 10Z" />
    <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
  </svg>
);

/* ─── Feedback Screen ───────────────────────────────────────────────── */
interface FeedbackScreenProps {
  visible: boolean;
  completedEntry: MeditationLogEntry | null;
  onDone: () => void;         // go to thank-you
  onNewSession: () => void;   // skip → back to player
}

function FeedbackScreen({ visible, completedEntry, onDone, onNewSession }: FeedbackScreenProps) {
  const [selectedMood, setSelectedMood] = useState<MoodId | null>(null);
  const [nota, setNota] = useState('');
  const [saving, setSaving] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleMoodSelect = (mood: MoodId) => {
    setSelectedMood(mood);
    captureEvent('session_feedback_mood', {
      mood,
      duration: completedEntry?.duration ?? undefined,
      level: completedEntry?.level ?? undefined,
      music: completedEntry?.music ?? undefined,
      variation: completedEntry?.variation ?? undefined,
    });
    // Auto-focus textarea so mobile keyboard opens immediately
    setTimeout(() => textareaRef.current?.focus(), 300);
  };

  const handleSubmit = async () => {
    if (!selectedMood) return;
    setSaving(true);
    try {
      await supabase.from('session_feedback').insert({
        mood: selectedMood,
        nota: nota.trim() || null,
        duration: completedEntry?.duration ?? null,
        level: completedEntry?.level ?? null,
        music: completedEntry?.music ?? null,
        variation: completedEntry?.variation ?? null,
      });
      captureEvent('session_feedback_submitted', {
        mood: selectedMood ?? undefined,
        has_nota: nota.trim().length > 0,
        duration: completedEntry?.duration ?? undefined,
        level: completedEntry?.level ?? undefined,
        music: completedEntry?.music ?? undefined,
        variation: completedEntry?.variation ?? undefined,
      });
    } catch (err) {
      console.error('Feedback save failed:', err);
    } finally {
      setSaving(false);
      onDone();
    }
  };

  // Reset state whenever the screen becomes visible again
  useEffect(() => {
    if (visible) {
      setSelectedMood(null);
      setNota('');
      setSaving(false);
    }
  }, [visible]);

  return (
    <div className={`feedback-wrap${visible ? ' visible' : ''}`}>
      <div className="feedback-card">
        <div className="session-end-glyph">◎</div>
        <h2 className="feedback-title">Sesión completa</h2>
        <p className="feedback-subtitle">¿Cómo fue tu práctica?</p>

        {/* Mood grid */}
        <div className="mood-grid">
          {MOOD_OPTIONS.map(({ id, emoji, label }) => (
            <button
              key={id}
              className={`mood-btn${selectedMood === id ? ' selected' : ''}`}
              data-mood={id}
              onClick={() => handleMoodSelect(id)}
            >
              <span className="mood-emoji">{emoji}</span>
              <span className="mood-label">{label}</span>
            </button>
          ))}
        </div>

        {/* Textarea — appears immediately after mood tap, no extra click needed */}
        <div className={`nota-reveal${selectedMood ? ' open' : ''}`}>
          <textarea
            ref={textareaRef}
            className="nota-box"
            placeholder="Lo que surgió, lo que sentiste, lo que necesitás recordar…"
            value={nota}
            onChange={e => setNota(e.target.value)}
            rows={3}
          />
        </div>

        {selectedMood && (
          <button className="feedback-submit" onClick={handleSubmit} disabled={saving}>
            {saving ? 'Guardando…' : 'Guardar'}
          </button>
        )}

        <button className="feedback-skip" onClick={onNewSession}>
          Omitir · nueva sesión
        </button>
      </div>
    </div>
  );
}

/* ─── Thank-you Screen ──────────────────────────────────────────────── */
interface ThankyouScreenProps {
  visible: boolean;
  onNewSession: () => void;
  installAvailable: boolean;
  isIOS: boolean;
  isInstalled: boolean;
  onInstall: () => void;
}

function ThankyouScreen({ visible, onNewSession, installAvailable, isIOS, isInstalled, onInstall }: ThankyouScreenProps) {
  const showInstallCta = !isInstalled && (installAvailable || isIOS);
  return (
    <div className={`feedback-wrap${visible ? ' visible' : ''}`}>
      <div className="feedback-card">
        <div className="thankyou-wrap">
          <span className="thankyou-glyph">✦</span>
          <h2 className="thankyou-title">Gracias</h2>
          <p className="thankyou-sub">Tu experiencia nos ayuda a mejorar.</p>

          {/* Post-session install prompt */}
          {showInstallCta && (
            isIOS ? (
              <p style={{
                fontSize: '11px',
                color: 'rgba(160,148,240,0.55)',
                letterSpacing: '0.04em',
                textAlign: 'center',
                lineHeight: 1.6,
                marginTop: '0.5rem',
                marginBottom: '0.25rem',
              }}>
                📲 Instala la app: toca <strong>Compartir</strong> → <strong>Agregar a pantalla de inicio</strong>
              </p>
            ) : (
              <button
                className="install-thanks-btn"
                onClick={onInstall}
                style={{
                  width: '100%',
                  padding: '11px 0',
                  borderRadius: '30px',
                  border: '0.5px solid rgba(123,111,208,0.45)',
                  background: 'rgba(123,111,208,0.14)',
                  color: 'rgba(200,190,255,0.9)',
                  fontSize: '12px',
                  fontFamily: 'var(--font-ui)',
                  letterSpacing: '0.1em',
                  textTransform: 'uppercase',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease-out',
                  marginTop: '0.5rem',
                }}
                onMouseOver={e => {
                  e.currentTarget.style.background = 'rgba(123,111,208,0.26)';
                  e.currentTarget.style.borderColor = 'rgba(123,111,208,0.7)';
                }}
                onMouseOut={e => {
                  e.currentTarget.style.background = 'rgba(123,111,208,0.14)';
                  e.currentTarget.style.borderColor = 'rgba(123,111,208,0.45)';
                }}
              >
                📲 Instalar Bhavana
              </button>
            )
          )}

          <button className="new-session-btn" onClick={onNewSession}>
            Nueva sesión
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── App ───────────────────────────────────────────────────────────── */
export default function App() {
  const [repoLog, setRepoLog] = useState<MeditationLog | null>(null);
  const [backgroundsLog, setBackgroundsLog] = useState<BackgroundLog | null>(null);
  const [duracion, setDuracion] = useState<string>('');
  const [nivel, setNivel] = useState<string>('');
  const [musica, setMusica] = useState<string>('');
  const [tipo, setTipo] = useState<boolean | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [backgroundAudioUrl, setBackgroundAudioUrl] = useState<string | null>(null);
  const [selectedEntry, setSelectedEntry] = useState<MeditationLogEntry | null>(null);
  const [loadingOptions, setLoadingOptions] = useState<boolean>(true);

  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(0.75);
  const [backgroundVolume, setBackgroundVolume] = useState(0.15); // very subtle background level

  // PWA install prompt
  const [installPrompt, setInstallPrompt] = useState<Event | null>(null);
  const [showInstallBanner, setShowInstallBanner] = useState(false);

  // Detect iOS (no beforeinstallprompt support) and standalone mode
  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
  const isInstalled = window.matchMedia('(display-mode: standalone)').matches;

  // Screen state: 'player' | 'feedback' | 'thankyou'
  const [screen, setScreen] = useState<AppScreen>('player');
  // The entry that just completed, kept for PostHog context in feedback
  const [completedEntry, setCompletedEntry] = useState<MeditationLogEntry | null>(null);

  const audioRef = useRef<HTMLAudioElement>(null);
  const backgroundAudioRef = useRef<HTMLAudioElement>(null);
  const tickRef = useRef<number | null>(null);

  /* init PostHog */
  useEffect(() => { initPostHog(); }, []);

  /* Capture the PWA install prompt event */
  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault(); // Prevent Chrome from showing the auto-prompt
      setInstallPrompt(e); // Store the event so we can trigger it later
      setShowInstallBanner(true); // Show our custom install button
    };
    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  const handleInstallClick = () => {
    if (!installPrompt) return;
    (installPrompt as any).prompt(); // Show the install dialog
    (installPrompt as any).userChoice.then((result: { outcome: string }) => {
      captureEvent('pwa_install', { outcome: result.outcome });
      setShowInstallBanner(false);
      setInstallPrompt(null);
    });
  };

  /* fetch logs */
  useEffect(() => {
    (async () => {
      try {
        const [medRes, bgRes] = await Promise.all([
          fetch('/meditations_repo_log.json'),
          fetch('/backgrounds_log.json'),
        ]);
        if (medRes.ok) setRepoLog(await medRes.json());
        if (bgRes.ok) setBackgroundsLog(await bgRes.json());
      } catch (e) {
        console.error(e);
      } finally {
        setLoadingOptions(false);
      }
    })();
  }, []);

  /* sync voice volume */
  useEffect(() => {
    if (audioRef.current) audioRef.current.volume = volume;
  }, [volume]);

  /* sync background volume */
  useEffect(() => {
    if (backgroundAudioRef.current) backgroundAudioRef.current.volume = backgroundVolume;
  }, [backgroundVolume]);

  /* tick timer — driven by the main voice audio element */
  useEffect(() => {
    if (playing) {
      tickRef.current = window.setInterval(() => {
        const a = audioRef.current;
        if (!a) return;
        setCurrentTime(Math.floor(a.currentTime));
        if (a.ended) {
          setPlaying(false);
          setCurrentTime(0);
          clearInterval(tickRef.current!);
        }
      }, 500);
    } else {
      if (tickRef.current) clearInterval(tickRef.current);
    }
    return () => { if (tickRef.current) clearInterval(tickRef.current); };
  }, [playing]);

  const allEntries = repoLog?.meditations ?? [];

  const getUniqueDurations = () =>
    Array.from(new Set(allEntries.map(e => e.duration))).sort(
      (a, b) => parseDurationMinutes(a) - parseDurationMinutes(b)
    );

  const getUniqueLevels = () =>
    Array.from(new Set(allEntries.map(e => e.level))).filter((l): l is string => l !== null).sort().reverse();

  const getUniqueMusicOptions = () =>
    Array.from(new Set(allEntries.map(e => e.music))).sort();

  /** Normalize guided: missing guided field + non-null level → guided=true */
  const getGuidedNormalized = (e: MeditationLogEntry): boolean =>
    e.guided === undefined ? e.level !== null : e.guided;

  const getUniqueGuidedOptions = (): boolean[] =>
    Array.from(new Set(allEntries.map(e => getGuidedNormalized(e)))).sort((a, b) => a === b ? 0 : a ? -1 : 1);

  const getMatchingEntries = (): MeditationLogEntry[] => {
    if (!duracion || !musica || tipo === null) return [];
    if (tipo === true && !nivel) return [];
    if (tipo === true) {
      return allEntries.filter(
        e => e.duration === duracion && e.level === nivel && e.music === musica && getGuidedNormalized(e) === true
      );
    }
    return allEntries.filter(
      e => e.duration === duracion && e.level === null && e.music === musica && getGuidedNormalized(e) === false
    );
  };

  const isAvailable = (): boolean => {
    const matches = getMatchingEntries();
    if (matches.length === 0) return false;
    // For guided sessions, also require a matching background file
    if (tipo === true && !isBackgroundAvailable(backgroundsLog, duracion, musica)) return false;
    return true;
  };
  const allSelected = tipo === null
    ? false
    : tipo === true
      ? !!(duracion && nivel && musica)
      : !!(duracion && musica);

  const handlePlay = () => {
    const matches = getMatchingEntries();
    if (!matches.length) return;

    const entry = matches[Math.floor(Math.random() * matches.length)];
    const url = buildR2Url(entry);
    const bgUrl = buildBackgroundUrl(entry);

    setSelectedEntry(entry);
    setAudioUrl(url);
    setBackgroundAudioUrl(bgUrl);
    setCurrentTime(0);
    setPlaying(false);
    setScreen('player'); // make sure we're on the player

    captureEvent('meditation_started', {
      duration: entry.duration,
      level: entry.level ?? undefined,
      music: entry.music,
      variation: entry.variation ?? undefined,
      model: entry.model ?? undefined,
    });

    setTimeout(() => {
      const a = audioRef.current;
      const bg = backgroundAudioRef.current;
      if (!a) return;

      // Load voice audio
      a.load();
      a.volume = volume; // 👈 ADD THIS LINE

      // Load and start background audio
      if (bg && bgUrl) {
        bg.load();
        bg.volume = backgroundVolume; // 👈 ADD THIS LINE
        bg.play().catch(console.error);
      }

      a.play().then(() => setPlaying(true)).catch(console.error);
      setDuration(0);
    }, 50);
  };

  const togglePlayPause = () => {
    const a = audioRef.current;
    const bg = backgroundAudioRef.current;
    if (!a || !audioUrl) return;
    if (playing) {
      a.pause();
      if (bg) bg.pause();
      setPlaying(false);
      captureEvent('meditation_paused', selectedEntry ? {
        duration: selectedEntry.duration,
        level: selectedEntry.level ?? undefined,
        music: selectedEntry.music,
        variation: selectedEntry.variation ?? undefined,
        progress_seconds: currentTime,
        progress_pct: progressPct,
      } : undefined);
    } else {
      a.play().then(() => setPlaying(true)).catch(console.error);
      if (bg) bg.play().catch(console.error);
    }
  };

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    const a = audioRef.current;
    const bg = backgroundAudioRef.current;
    if (!a || !duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const newTime = pct * duration;
    a.currentTime = newTime;
    if (bg) bg.currentTime = newTime;
    setCurrentTime(Math.floor(newTime));
  };

  /* When the background finishes loading metadata, sync its position to follow the voice */
  useEffect(() => {
    const bg = backgroundAudioRef.current;
    const a = audioRef.current;
    if (!bg || !a) return;

    const onBgLoaded = () => {
      bg.currentTime = a.currentTime;
    };

    bg.addEventListener('loadedmetadata', onBgLoaded);
    return () => bg.removeEventListener('loadedmetadata', onBgLoaded);
  }, [backgroundAudioUrl]);

  /* Session ended → begin gong crossfade into feedback */
  const handleSessionEnd = () => {
    setPlaying(false);
    setCurrentTime(0);
    captureEvent('meditation_completed', selectedEntry ? {
      duration: selectedEntry.duration,
      level: selectedEntry.level ?? undefined,
      music: selectedEntry.music,
      variation: selectedEntry.variation ?? undefined,
    } : undefined);
    setCompletedEntry(selectedEntry);
    // The gongs are the last ~15s of the audio, so by the time onEnded fires
    // the transition is already emotionally complete. We start the fade immediately.
    setScreen('feedback');
  };

  const handleFeedbackDone = () => { setScreen('thankyou'); };

  const handleNewSession = () => {
    setScreen('player');
    setAudioUrl(null);
    setBackgroundAudioUrl(null);
    setSelectedEntry(null);
    setCompletedEntry(null);
    setPlaying(false);
    setCurrentTime(0);
  };

  const progressPct = duration > 0 ? Math.round((currentTime / duration) * 100) : 0;
  const selectionComplete = allSelected && isAvailable();
  const isGuided = tipo === true;

  return (
    <>
      <style>{css}</style>

      <div className="backdrop" />

      {/*
        We keep player + feedback in the same stacking context.
        The player fades out as feedback fades in via CSS opacity transitions.
      */}
      <div style={{ position: 'relative', minHeight: '100vh' }}>

        {/* ── Ambient orbs (shared across screens) ── */}
        <div className="orb orb-1" />
        <div className="orb orb-2" />
        <div className="orb orb-3" />

        {/* ── PLAYER SCREEN ── */}
        <div className={`shell fade-wrap${screen !== 'player' ? ' hidden' : ''}`}>
          <div className="card">
            {/* Header */}
            <p className="tod">{getTimeOfDay()}</p>
            <h1 className="brand-title">Bhavana</h1>
            <p className="tagline">un momento solo para ti</p>

            {/* PWA install — three cases: already installed, Chrome/Android prompt, iOS manual */}
            {!isInstalled && (
              <>
                {/* Chrome / Android: show banner when beforeinstallprompt has fired */}
                {showInstallBanner && (
                  <div className="install-banner">
                    <span className="install-banner-text">
                      Instala Bhavana en tu dispositivo
                    </span>
                    <button className="install-banner-btn" onClick={handleInstallClick}>
                      Instalar
                    </button>
                    <button
                      className="install-banner-close"
                      onClick={() => setShowInstallBanner(false)}
                      aria-label="Cerrar"
                    >
                      ✕
                    </button>
                  </div>
                )}

                {/* Chrome / Android: subtle text link as fallback when banner was dismissed
                    or hasn't appeared yet but the prompt is available */}
                {!showInstallBanner && installPrompt && (
                  <div style={{ textAlign: 'center', marginBottom: '1.25rem' }}>
                    <button
                      onClick={handleInstallClick}
                      style={{
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        fontSize: '11px',
                        color: 'rgba(160,148,240,0.45)',
                        textDecoration: 'underline',
                        textUnderlineOffset: '3px',
                        letterSpacing: '0.04em',
                        fontFamily: 'var(--font-ui)',
                        padding: 0,
                        transition: 'color 0.18s',
                      }}
                      onMouseOver={e => (e.currentTarget.style.color = 'rgba(168,159,232,0.85)')}
                      onMouseOut={e => (e.currentTarget.style.color = 'rgba(160,148,240,0.45)')}
                    >
                      Instalar app
                    </button>
                  </div>
                )}

                {/* iOS Safari: no beforeinstallprompt — show manual instructions */}
                {isIOS && !installPrompt && (
                  <div className="install-banner ios-install-banner" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '6px' }}>
                    <span className="install-banner-text" style={{ fontWeight: 400 }}>
                      Para instalar en iPhone o iPad:
                    </span>
                    <span className="install-banner-text" style={{ opacity: 0.7 }}>
                      Toca <strong>Compartir</strong> (□↑) → <strong>Agregar a pantalla de inicio</strong>
                    </span>
                    <button
                      className="install-banner-close"
                      aria-label="Cerrar"
                      style={{ alignSelf: 'flex-end', marginTop: '-28px' }}
                      onClick={() => {
                        const el = document.querySelector('.ios-install-banner') as HTMLElement | null;
                        if (el) el.style.display = 'none';
                      }}
                    >
                      ✕
                    </button>
                  </div>
                )}
              </>
            )}

            {loadingOptions && <p className="loading-msg">cargando sesiones…</p>}

            {!loadingOptions && (
              <>
                <div className="pill-group">
                  <p className="pill-label">Tipo de meditación</p>
                  <div className="pills">
                    {getUniqueGuidedOptions().map(g => (
                      <div
                        key={g ? 'guided' : 'unguided'}
                        className={`pill${tipo === g ? ' active' : ''}`}
                        onClick={() => { setTipo(g); setNivel(''); setAudioUrl(null); setBackgroundAudioUrl(null); setSelectedEntry(null); setPlaying(false); setCurrentTime(0); }}
                      >
                        {g ? 'Guiada' : 'En silencio'}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="pill-group">
                  <p className="pill-label">Duración</p>
                  <div className="pills">
                    {getUniqueDurations().map(d => (
                      <div
                        key={d}
                        className={`pill${duracion === d ? ' active' : ''}`}
                        onClick={() => { setDuracion(d); setAudioUrl(null); setBackgroundAudioUrl(null); setSelectedEntry(null); setPlaying(false); setCurrentTime(0); }}
                      >
                        {formatDuration(d)}
                      </div>
                    ))}
                  </div>
                </div>

                {(tipo === null || tipo === true) && (
                <div className="pill-group">
                  <p className="pill-label">Nivel</p>
                  <div className="pills">
                    {getUniqueLevels().map(l => (
                      <div
                        key={l}
                        className={`pill${nivel === l ? ' active' : ''}`}
                        onClick={() => { setNivel(l); setAudioUrl(null); setBackgroundAudioUrl(null); setSelectedEntry(null); setPlaying(false); setCurrentTime(0); }}
                      >
                        {capitalize(l ?? '')}
                      </div>
                    ))}
                  </div>
                </div>
                )}

                <div className="pill-group">
                  <p className="pill-label">Sonido de fondo</p>
                  <div className="pills">
                    {getUniqueMusicOptions().map(m => (
                      <div
                        key={m}
                        className={`pill${musica === m ? ' active' : ''}`}
                        onClick={() => { 
                          setMusica(m); 
                          
                          // Set dynamic initial volume based on the selection
                          if (m === 'nature') {
                            setBackgroundVolume(0.15);
                          } else if (m === 'binaural') {
                            setBackgroundVolume(0.75);
                          } else {
                            setBackgroundVolume(0.50); // Default fallback for silence or others
                          }

                          // Keep your existing resets
                          setAudioUrl(null); 
                          setBackgroundAudioUrl(null); 
                          setSelectedEntry(null); 
                          setPlaying(false); 
                          setCurrentTime(0); 
                        }}
                      >
                        {musicDisplayName(m)}
                      </div>
                    ))}
                  </div>
                </div>

                {allSelected && !isAvailable() && (
                  <p className="unavailable">esta combinación no está disponible aún</p>
                )}
              </>
            )}

            <div className="divider" />

            {/* Bottom row: play ring on left, volume sliders stacked on right */}
            <div className="bottom-row">
              <div className="bottom-left">
                <div
                  className={`ring${playing ? ' playing' : ''}`}
                  onClick={audioUrl ? togglePlayPause : (selectionComplete ? handlePlay : undefined)}
                  role="button"
                  aria-label={playing ? 'Pausar meditación' : 'Iniciar meditación'}
                  style={{ cursor: selectionComplete || audioUrl ? 'pointer' : 'default', opacity: selectionComplete || audioUrl ? 1 : 0.4 }}
                >
                  <span className="ring-icon">
                    {playing ? <IconPause /> : <IconPlay />}
                  </span>
                </div>
              </div>

              <div className="vol-stack">
                <div className="vol-wrap">
                  <IconVolume />
                  <input
                    type="range"
                    className="vol-slider"
                    min={0} max={1} step={0.01}
                    value={volume}
                    onChange={e => setVolume(parseFloat(e.target.value))}
                    aria-label="Volumen"
                  />
                </div>

                {isGuided && selectedEntry && (
                  <div className="vol-wrap">
                    <IconLeaf />
                    <input
                      type="range"
                      className="vol-slider"
                      min={0} max={1} step={0.01}
                      value={backgroundVolume}
                      onChange={e => setBackgroundVolume(parseFloat(e.target.value))}
                      aria-label="Volumen de fondo"
                    />
                  </div>
                )}
              </div>
            </div>

            <p className={`session-label${selectedEntry ? ' active' : ''}`}>
              {selectedEntry
                ? `${formatDuration(selectedEntry.duration)} · ${capitalize(selectedEntry.level ?? '')} · ${musicDisplayName(selectedEntry.music)} · var. ${selectedEntry.variation ?? '-'}`
                : allSelected && !isAvailable()
                  ? ''
                  : 'elige tu sesión y presiona para comenzar'}
            </p>

            {/* Progress */}
            <div className="progress-area">
              <div className="progress-track" onClick={handleSeek}>
                <div className="progress-fill" style={{ width: `${progressPct}%` }} />
              </div>
              <div className="time-labels">
                <span>{formatTime(currentTime)}</span>
                <span>{duration > 0 ? formatTime(Math.floor(duration)) : '--:--'}</span>
              </div>
            </div>

            {/* Download button below progress bar */}
            <div className="download-row">
              <a
                className="icon-btn"
                href={audioUrl ?? '#'}
                download={selectedEntry ? `${parseDurationMinutes(selectedEntry.duration)}_${selectedEntry.level ?? ''}_${selectedEntry.variation ?? ''}.opus` : undefined}
                aria-label="Descargar meditación"
                title="Descargar"
                style={{ pointerEvents: audioUrl ? 'auto' : 'none', opacity: audioUrl ? 1 : 0.2, textDecoration: 'none' }}
                onClick={() => captureEvent('meditation_downloaded', selectedEntry ? {
                  duration: selectedEntry.duration,
                  level: selectedEntry.level ?? undefined,
                  music: selectedEntry.music,
                  variation: selectedEntry.variation ?? undefined,
                } : undefined)}
              >
                <IconDownload />
              </a>
            </div>

          </div>
        </div>

        {/* ── FEEDBACK SCREEN ── */}
        <FeedbackScreen
          visible={screen === 'feedback'}
          completedEntry={completedEntry}
          onDone={handleFeedbackDone}
          onNewSession={handleNewSession}
        />

        {/* ── THANK-YOU SCREEN ── */}
        <ThankyouScreen
          visible={screen === 'thankyou'}
          onNewSession={handleNewSession}
          installAvailable={installPrompt !== null}
          isIOS={isIOS}
          isInstalled={isInstalled}
          onInstall={handleInstallClick}
        />
      </div>

      {/* Hidden voice audio element */}
      {audioUrl && (
        <audio
          ref={audioRef}
          src={audioUrl}
          onLoadedMetadata={() => { if (audioRef.current) setDuration(audioRef.current.duration); }}
          onEnded={handleSessionEnd}
        />
      )}

      {/* Hidden background audio element — plays simultaneously with voice for guided sessions */}
      {isGuided && backgroundAudioUrl && (
        <audio
          ref={backgroundAudioRef}
          src={backgroundAudioUrl}
        />
      )}
    </>
  );
}