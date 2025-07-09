import React from 'react';
import './App.css';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>Contemplative AI - Audio Player</h1>
        <p>Listen to the meditation audio below:</p>
      </header>
      <main>
        <audio controls style={{ width: '100%', marginTop: '2rem' }}>
          <source src={process.env.PUBLIC_URL + '/voz_kokoro.wav'} type="audio/wav" />
          Your browser does not support the audio element.
        </audio>
        <div style={{ marginTop: '1rem', color: '#888' }}>
          <span>File: voz_kokoro.wav</span>
        </div>
      </main>
    </div>
  );
}

export default App;
