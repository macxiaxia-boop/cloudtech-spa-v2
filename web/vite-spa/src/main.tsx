import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { AuthProvider } from './contexts/AuthContext';
import { I18nProvider } from './i18n';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <I18nProvider>
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </I18nProvider>
  </React.StrictMode>
);

// Installable app shell: service worker caches only public hashed bundles and
// a truthful offline explanation. API/tenant/client data is never cached.
if ('serviceWorker' in navigator &&
    (window.location.protocol === 'https:' || /^(localhost|127\\.0\\.0\\.1)$/.test(window.location.hostname))) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js', { scope: '/' })
      .catch((error) => console.warn('[CloudTech] Offline shell unavailable:', error));
  }, { once: true });
}
