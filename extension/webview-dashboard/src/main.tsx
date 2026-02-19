import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

// In standalone web mode (not VS Code), load the web theme that provides
// --vscode-* CSS custom property values. Detection: acquireVsCodeApi is
// only defined inside a VS Code webview.
if (typeof (window as any).acquireVsCodeApi === 'undefined') {
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = new URL('./web-theme.css', import.meta.url).href;
  document.head.appendChild(link);
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
