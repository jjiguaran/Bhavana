import React, { useState } from 'react';
import './App.css';

interface AudioFile {
  name: string;
  path: string;
  displayName: string;
}

const audioFiles: AudioFile[] = [
  { name: 'voz_kokoro.wav', path: '/voz_kokoro.wav', displayName: 'Voz Kokoro' },
  { name: 'meditacion_kokoro.wav', path: '/meditacion_kokoro.wav', displayName: 'Meditación Kokoro' },
  { name: 'meditacion_kokoro_2.wav', path: '/meditacion_kokoro_2.wav', displayName: 'Meditación Kokoro 2' }
];

function App() {
  const [selectedAudio, setSelectedAudio] = useState<AudioFile>(audioFiles[0]);

  const handleAudioChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const selected = audioFiles.find(file => file.name === event.target.value);
    if (selected) {
      setSelectedAudio(selected);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Contemplative AI - Audio Player</h1>
        <p>Select and listen to meditation audio:</p>
      </header>
      <main>
        <div className="audio-selector">
          <label htmlFor="audio-select">Choose Audio File:</label>
          <select 
            id="audio-select" 
            value={selectedAudio.name} 
            onChange={handleAudioChange}
            className="audio-dropdown"
          >
            {audioFiles.map((file) => (
              <option key={file.name} value={file.name}>
                {file.displayName}
              </option>
            ))}
          </select>
        </div>
        
        <div className="audio-player">
          <audio 
            key={selectedAudio.name}
            controls 
            style={{ width: '100%', marginTop: '1rem' }}
          >
            <source src={process.env.PUBLIC_URL + selectedAudio.path} type="audio/wav" />
            Your browser does not support the audio element.
          </audio>
          <div className="file-info">
            <span>Currently playing: {selectedAudio.displayName}</span>
            <span>File: {selectedAudio.name}</span>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
