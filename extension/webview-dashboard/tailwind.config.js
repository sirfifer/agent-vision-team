/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        vscode: {
          bg: 'var(--vscode-editor-background)',
          fg: 'var(--vscode-foreground)',
          'widget-bg': 'var(--vscode-editorWidget-background)',
          border: 'var(--vscode-widget-border)',
          'btn-bg': 'var(--vscode-button-background)',
          'btn-fg': 'var(--vscode-button-foreground)',
          'btn-hover': 'var(--vscode-button-hoverBackground)',
          'btn2-bg': 'var(--vscode-button-secondaryBackground)',
          'btn2-fg': 'var(--vscode-button-secondaryForeground)',
          muted: 'var(--vscode-descriptionForeground)',
        },
        tier: {
          vision: '#f14c4c',
          architecture: '#cca700',
          quality: '#4ec9b0',
        },
        agent: {
          active: '#4ec9b0',
          idle: '#6c6c6c',
        },
      },
      fontSize: {
        '2xs': '0.65rem',
      },
    },
  },
  plugins: [],
};
