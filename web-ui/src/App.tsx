import React, { useState, useEffect } from 'react';
import './App.css';

interface MeditationOption {
  minutes: number;
  level: string;
  music: boolean;
  display_name: string;
}

function App() {
  const [duracion, setDuracion] = useState<number | "">("");
  const [nivel, setNivel] = useState<string>("");
  const [musica, setMusica] = useState<string>("");
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [availableMeditations, setAvailableMeditations] = useState<MeditationOption[]>([]);
  const [loadingOptions, setLoadingOptions] = useState<boolean>(true);

  // Fetch available meditation combinations on component mount
  useEffect(() => {
    const fetchAvailableMeditations = async () => {
      try {
        const response = await fetch("http://localhost:8000/available-meditations");
        if (response.ok) {
          const data = await response.json();
          setAvailableMeditations(data.data || []);
        }
      } catch (err) {
        console.error("Error fetching available meditations:", err);
      } finally {
        setLoadingOptions(false);
      }
    };

    fetchAvailableMeditations();
  }, []);

  // Get unique values for dropdowns
  const getUniqueDurations = () => Array.from(new Set(availableMeditations.map(m => m.minutes))).sort((a, b) => a - b);
  const getUniqueLevels = () => Array.from(new Set(availableMeditations.map(m => m.level))).sort();
  const getUniqueMusicOptions = () => Array.from(new Set(availableMeditations.map(m => m.music))).sort();

  // Check if current combination is available
  const isCombinationAvailable = () => {
    return availableMeditations.some(m => 
      m.minutes === duracion && 
      m.level === nivel && 
      m.music === (musica === "con_musica")
    );
  };

  const handleGenerate = async () => {
    if (!duracion || !nivel || !musica) return;

    setLoading(true);
    setAudioUrl(null);

    try {
      const response = await fetch("http://localhost:8000/get-meditation", {
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
        {loadingOptions && <p style={{ color: '#666', fontSize: '0.9rem' }}>Cargando opciones disponibles...</p>}
        {!loadingOptions && availableMeditations.length === 0 && (
          <p style={{ color: '#ff6b6b', fontSize: '0.9rem' }}>No hay meditaciones disponibles en este momento.</p>
        )}
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
              {getUniqueDurations().map((d: number) => (
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
              {getUniqueLevels().map((l: string) => (
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
              {getUniqueMusicOptions().map((music: boolean) => (
                <option key={music.toString()} value={music ? "con_musica" : "mute"}>
                  {music ? "Con música" : "Sin música"}
                </option>
              ))}
            </select>
          </label>
          <button
            onClick={handleGenerate}
            disabled={!duracion || !nivel || !musica || loading || loadingOptions || !isCombinationAvailable()}
            style={{ marginTop: '1rem' }}
          >
            {loading ? "Generando..." : loadingOptions ? "Cargando..." : "Generar meditación"}
          </button>
          {!loadingOptions && duracion && nivel && musica && !isCombinationAvailable() && (
            <p style={{ color: '#ff6b6b', fontSize: '0.9rem', marginTop: '0.5rem' }}>
              Esta combinación no está disponible. Por favor selecciona otra opción.
            </p>
          )}
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
