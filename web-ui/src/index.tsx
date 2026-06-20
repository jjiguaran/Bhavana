import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import * as serviceWorkerRegistration from './serviceWorkerRegistration';

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// Register the service worker for PWA support (offline capabilities,
// install prompt, faster subsequent loads).
// Unregister() to opt-out; see https://cra.link/PWA
serviceWorkerRegistration.register();

