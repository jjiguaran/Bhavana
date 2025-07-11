import React, { useState } from 'react';
import './App.css';

interface AudioFile {
  name: string;
  path: string;
  displayName: string;
}

const DURATIONS = [5, 10];
const LEVELS = ["principiante", "avanzado"];
const MUSIC_OPTIONS = ["con_musica", "_mute"];

function App() {
  const [duracion, setDuracion] = useState<number | "">("");
  const [nivel, setNivel] = useState<string>("");
  const [musica, setMusica] = useState<string>("");

  let audioFileName = "";
  let audioFilePath = "";
  if (duracion && nivel && musica) {
    audioFileName = `meditacion_kokoro_${duracion}_${nivel}_${musica}.wav`;
    audioFilePath = `/data/audio/${audioFileName}`;
  }

  return (
    <div className="App">
      <header className="App-header">
        <h1>Contemplative AI - Audio Player</h1>
        <p>Filtra y escucha meditaciones:</p>
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
        </div>
        {audioFileName && (
          <div className="audio-player">
            <audio
              key={audioFileName}
              controls
              style={{ width: '100%', marginTop: '1rem' }}
            >
              <source src={process.env.PUBLIC_URL + audioFilePath} type="audio/wav" />
              Tu navegador no soporta el elemento de audio.
            </audio>
            <div className="file-info">
              <span>Archivo: {audioFileName}</span>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
