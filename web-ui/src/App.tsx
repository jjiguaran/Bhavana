import React, { useState, useEffect, useRef } from 'react';

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

  /* ── Ambient orbs — scale up on desktop so they fill the viewport ── */
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
    width: 96px;
    height: 96px;
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
    width: 76px; height: 76px;
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

  /* SVG play/pause icons */
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

  /* ── Bottom row ── */
  .bottom-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
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
    flex: 1;
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

  /* ── Hidden audio element ── */
  audio { display: none; }

  /* ── Error state ── */
  .error-msg {
    text-align: center;
    font-size: 12px;
    color: rgba(232,184,122,0.7);
    margin-top: 0.5rem;
    letter-spacing: 0.03em;
  }
`;

/* ─── Types ─────────────────────────────────────────────────────────── */
interface MeditationLogEntry {
  duration: string;
  level: string;
  variation: number;
  model: string;
  date_generated: string;
  music: string;
}

interface MeditationLog {
  meditations: MeditationLogEntry[];
}

/* ─── Constants ─────────────────────────────────────────────────────── */
const R2_BUCKET_URL = "https://pub-e5092eb6363d42ce8ac557dbecc589f0.r2.dev";

/* ─── Helpers ───────────────────────────────────────────────────────── */
function parseDurationMinutes(duration: string): number {
  const match = duration.match(/(\d+)/);
  return match ? parseInt(match[1], 10) : 0;
}

function buildR2Url(entry: MeditationLogEntry): string {
  const durationNum = parseDurationMinutes(entry.duration);
  return `${R2_BUCKET_URL}/meditations/${entry.music}/${durationNum}_${entry.level}_${entry.variation}.opus`;
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

const IconShuffle = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="16 3 21 3 21 8" />
    <line x1="4" y1="20" x2="21" y2="3" />
    <polyline points="21 16 21 21 16 21" />
    <line x1="15" y1="15" x2="21" y2="21" />
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

/* ─── App ───────────────────────────────────────────────────────────── */
export default function App() {
  const [repoLog, setRepoLog] = useState<MeditationLog | null>(null);
  const [duracion, setDuracion] = useState<string>('');
  const [nivel, setNivel] = useState<string>('');
  const [musica, setMusica] = useState<string>('');
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [selectedEntry, setSelectedEntry] = useState<MeditationLogEntry | null>(null);
  const [loadingOptions, setLoadingOptions] = useState<boolean>(true);

  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(0.75);

  const audioRef = useRef<HTMLAudioElement>(null);
  const tickRef = useRef<number | null>(null);

  /* fetch log */
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch('/meditations_repo_log.json');
        if (res.ok) setRepoLog(await res.json());
      } catch (e) {
        console.error(e);
      } finally {
        setLoadingOptions(false);
      }
    })();
  }, []);

  /* sync volume */
  useEffect(() => {
    if (audioRef.current) audioRef.current.volume = volume;
  }, [volume]);

  /* tick timer */
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
    Array.from(new Set(allEntries.map(e => e.level))).sort();

  const getUniqueMusicOptions = () =>
    Array.from(new Set(allEntries.map(e => e.music))).sort();

  const getMatchingEntries = (): MeditationLogEntry[] => {
    if (!duracion || !nivel || !musica) return [];
    return allEntries.filter(
      e => e.duration === duracion && e.level === nivel && e.music === musica
    );
  };

  const isAvailable = () => getMatchingEntries().length > 0;
  const allSelected = !!(duracion && nivel && musica);

  const handlePlay = () => {
    const matches = getMatchingEntries();
    if (!matches.length) return;

    const entry = matches[Math.floor(Math.random() * matches.length)];
    const url = buildR2Url(entry);

    setSelectedEntry(entry);
    setAudioUrl(url);
    setCurrentTime(0);
    setPlaying(false);

    // give React a tick to render the <audio> with new src
    setTimeout(() => {
      const a = audioRef.current;
      if (!a) return;
      a.load();
      a.play().then(() => setPlaying(true)).catch(console.error);
      setDuration(0); // will be set by onLoadedMetadata
    }, 50);
  };

  const handleShuffle = () => {
    handlePlay();
  };

  const togglePlayPause = () => {
    const a = audioRef.current;
    if (!a || !audioUrl) return;
    if (playing) {
      a.pause();
      setPlaying(false);
    } else {
      a.play().then(() => setPlaying(true)).catch(console.error);
    }
  };

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    const a = audioRef.current;
    if (!a || !duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    a.currentTime = pct * duration;
    setCurrentTime(Math.floor(pct * duration));
  };

  const progressPct = duration > 0 ? Math.round((currentTime / duration) * 100) : 0;

  const variantCount = getMatchingEntries().length;
  const selectionComplete = allSelected && isAvailable();

  return (
    <>
      <style>{css}</style>

      {/* Full-viewport dark backdrop — fills the whole screen on desktop */}
      <div className="backdrop" />

      <div className="shell">
        {/* Ambient orbs — vw-based so they scale with the viewport */}
        <div className="orb orb-1" />
        <div className="orb orb-2" />
        <div className="orb orb-3" />

        <div className="card">
          {/* Header */}
          <p className="tod">{getTimeOfDay()}</p>
          <h1 className="brand-title">Bhavana</h1>
          <p className="tagline">un momento solo para ti</p>

          {/* Loading */}
          {loadingOptions && <p className="loading-msg">cargando sesiones…</p>}

          {/* Pills */}
          {!loadingOptions && (
            <>
              <div className="pill-group">
                <p className="pill-label">Duración</p>
                <div className="pills">
                  {getUniqueDurations().map(d => (
                    <div
                      key={d}
                      className={`pill${duracion === d ? ' active' : ''}`}
                      onClick={() => { setDuracion(d); setAudioUrl(null); setSelectedEntry(null); setPlaying(false); setCurrentTime(0); }}
                    >
                      {formatDuration(d)}
                    </div>
                  ))}
                </div>
              </div>

              <div className="pill-group">
                <p className="pill-label">Nivel</p>
                <div className="pills">
                  {getUniqueLevels().map(l => (
                    <div
                      key={l}
                      className={`pill${nivel === l ? ' active' : ''}`}
                      onClick={() => { setNivel(l); setAudioUrl(null); setSelectedEntry(null); setPlaying(false); setCurrentTime(0); }}
                    >
                      {capitalize(l)}
                    </div>
                  ))}
                </div>
              </div>

              <div className="pill-group">
                <p className="pill-label">Música</p>
                <div className="pills">
                  {getUniqueMusicOptions().map(m => (
                    <div
                      key={m}
                      className={`pill${musica === m ? ' active' : ''}`}
                      onClick={() => { setMusica(m); setAudioUrl(null); setSelectedEntry(null); setPlaying(false); setCurrentTime(0); }}
                    >
                      {capitalize(m)}
                    </div>
                  ))}
                </div>
              </div>

              {/* Unavailable notice */}
              {allSelected && !isAvailable() && (
                <p className="unavailable">esta combinación no está disponible aún</p>
              )}
            </>
          )}

          <div className="divider" />

          {/* Breathing ring */}
          <div className="ring-wrap">
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

            <p className={`session-label${selectedEntry ? ' active' : ''}`}>
              {selectedEntry
                ? `${formatDuration(selectedEntry.duration)} · ${capitalize(selectedEntry.level)} · ${capitalize(selectedEntry.music)} · var. ${selectedEntry.variation}`
                : allSelected && !isAvailable()
                  ? ''
                  : 'elige tu sesión y presiona para comenzar'}
            </p>
          </div>

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

          {/* Bottom controls */}
          <div className="bottom-row">
            <button
              className="icon-btn"
              onClick={handleShuffle}
              disabled={!selectionComplete}
              aria-label="Otra variación aleatoria"
              title="Otra variación"
            >
              <IconShuffle />
            </button>

            <div className="vol-wrap">
              <IconVolume />
              <input
                type="range"
                className="vol-slider"
                min={0}
                max={1}
                step={0.01}
                value={volume}
                onChange={e => setVolume(parseFloat(e.target.value))}
                aria-label="Volumen"
              />
            </div>

            <a
              className="icon-btn"
              href={audioUrl ?? '#'}
              download={selectedEntry
                ? `${parseDurationMinutes(selectedEntry.duration)}_${selectedEntry.level}_${selectedEntry.variation}.opus`
                : undefined}
              aria-label="Descargar meditación"
              title="Descargar"
              style={{ pointerEvents: audioUrl ? 'auto' : 'none', opacity: audioUrl ? 1 : 0.2, textDecoration: 'none' }}
            >
              <IconDownload />
            </a>
          </div>

          {/* Variation hint */}
          {selectionComplete && (
            <p className="var-hint">
              {variantCount} variación{variantCount !== 1 ? 'es' : ''} disponible{variantCount !== 1 ? 's' : ''}
              {variantCount > 1 && (
                <> · <button onClick={handleShuffle}>cambiar variación</button></>
              )}
            </p>
          )}
        </div>
      </div>

      {/* Hidden real audio element */}
      {audioUrl && (
        <audio
          ref={audioRef}
          src={audioUrl}
          onLoadedMetadata={() => {
            if (audioRef.current) setDuration(audioRef.current.duration);
          }}
          onEnded={() => { setPlaying(false); setCurrentTime(0); }}
        />
      )}
    </>
  );
}
