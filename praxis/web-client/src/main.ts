import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';
import { PlotlyService } from 'angular-plotly.js';

// Plotly is loaded globally via angular.json scripts (window.Plotly)
// Configure angular-plotly.js to use the global reference
PlotlyService.setPlotly((window as any).Plotly);

import { environment } from './environments/environment';
import { GlobalInjector } from './app/core/utils/global-injector';

// Pre-bootstrap configuration checks
if ((environment as any).browserMode) {
  console.log('[main.ts] Detected Browser Mode from environment. Setting localStorage flag.');
  localStorage.setItem('praxis_mode', 'browser');
}

bootstrapApplication(App, appConfig)
  .then(async (appRef) => {
    GlobalInjector.set(appRef.injector);

    // Pre-warm Pyodide worker in background for faster Playground access
    // This runs non-blocking - user won't wait for it
    try {
      const { PyodidePoolService } = await import('./app/core/services/pyodide-pool.service');
      const poolService = appRef.injector.get(PyodidePoolService);
      poolService.preWarm();
      console.log('[main.ts] Started Pyodide pre-warm in background');
    } catch (err) {
      console.warn('[main.ts] Failed to pre-warm Pyodide:', err);
    }
  })
  .catch((err) => console.error(err));

