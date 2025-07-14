import React, { useState } from 'react';
import './App.css';

const DURATIONS = [5, 10];
const LEVELS = ["principiante", "avanzado"];
const MUSIC_OPTIONS = ["con_musica", "mute"];

function App() {
  const [duracion, setDuracion] = useState<number | "">("");
  const [nivel, setNivel] = useState<string>("");
  const [musica, setMusica] = useState<string>("");
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const handleGenerate = async () => {
    if (!duracion || !nivel || !musica) return;

    setLoading(true);
    setAudioUrl(null);

    try {
      const response = await fetch("http://localhost:8000/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          minutes: duracion,
          nivel,
          musica: musica === "con_musica",
          path_binaural: "../data/audio/simply-meditation-series-11hz-alpha-binaural-waves-for-relaxed-focus-8028.mp3", // adjust if needed
        }),
      });

      if (!response.ok) {
        throw new Error("Error al generar el audio");
      }

      // Create object URL for audio blob
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      setAudioUrl(url);
    } catch (err) {
      console.error(err);
      alert("Ocurrió un error generando la meditación.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Contemplative AI - Audio Player</h1>
        <p>Filtra y genera meditaciones guiadas personalizadas:</p>
      </header>
      <main>
        <div className="audio-selector">
          <label>Duración:
            <select
              value={duracion}
              onChange={e => setDuracion(Number(e.target.value))}
              className="audio-dropdown"
            >
              <option value="">Selecciona duración</option>
              {DURATIONS.map(d => (
                <option key={d} value={d}>{d} minutos</option>
              ))}
            </select>
          </label>
          <label>Nivel:
            <select
              value={nivel}
              onChange={e => setNivel(e.target.value)}
              className="audio-dropdown"
            >
              <option value="">Selecciona nivel</option>
              {LEVELS.map(l => (
                <option key={l} value={l}>{l.charAt(0).toUpperCase() + l.slice(1)}</option>
              ))}
            </select>
          </label>
          <label>Música:
            <select
              value={musica}
              onChange={e => setMusica(e.target.value)}
              className="audio-dropdown"
            >
              <option value="">Selecciona música</option>
              <option value="con_musica">Con música</option>
              <option value="mute">Sin música</option>
            </select>
          </label>
          <button
            onClick={handleGenerate}
            disabled={!duracion || !nivel || !musica || loading}
            style={{ marginTop: '1rem' }}
          >
            {loading ? "Generando..." : "Generar meditación"}
          </button>
        </div>

        {audioUrl && (
          <div className="audio-player">
            <audio controls src={audioUrl} style={{ width: '100%', marginTop: '1rem' }} />
            <div className="file-info">
              <a href={audioUrl} download={`meditacion_kokoro.wav`}>
                Descargar meditación
              </a>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
