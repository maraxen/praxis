import { inject } from '@angular/core';
import { Routes, Router, CanActivateFn } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { MainLayoutComponent } from './layout/main-layout.component';
import { UnifiedShellComponent } from './layout/unified-shell.component';
import { LoginComponent } from './features/auth/login.component';
import { RegisterComponent } from './features/auth/register.component';
import { ForgotPasswordComponent } from './features/auth/forgot-password.component';
import { SplashComponent } from './features/splash/splash.component';
import { ModeService } from './core/services/mode.service';

/**
 * Bypass splash page in browser mode.
 * When there's no auth backend (browser/GH-Pages), the splash serves no purpose.
 * Redirects to /app/home while preserving all query params (mode, dbName, etc.).
 */
const browserModeSplashGuard: CanActivateFn = () => {
  const modeService = inject(ModeService);
  if (modeService.isBrowserMode()) {
    const router = inject(Router);
    const params = new URLSearchParams(window.location.search);
    const queryParams: Record<string, string> = {};
    params.forEach((v, k) => queryParams[k] = v);
    return router.createUrlTree(['/app/home'], { queryParams });
  }
  return true;
};

export const routes: Routes = [
  // Public splash page — bypassed in browser mode (no auth = no splash needed)
  {
    path: '',
    canActivate: [browserModeSplashGuard],
    component: SplashComponent,
    pathMatch: 'full'
  },
  // Auth pages (no auth required)
  {
    path: 'login',
    component: LoginComponent
  },
  {
    path: 'register',
    component: RegisterComponent
  },
  {
    path: 'forgot-password',
    component: ForgotPasswordComponent
  },

  // Unified Shell Routes (App + Docs)
  {
    path: '',
    component: UnifiedShellComponent,
    children: [
      // Praxis App
      {
        path: 'app',
        canActivate: [authGuard],
        children: [
          { path: '', redirectTo: 'home', pathMatch: 'full' },
          {
            path: 'home',
            loadComponent: () => import('./features/home/home.component').then(m => m.HomeComponent)
          },
          {
            path: 'assets',
            loadChildren: () => import('./features/assets/asset.routes').then(m => m.ASSET_ROUTES)
          },
          {
            path: 'protocols',
            loadChildren: () => import('./features/protocols/protocol.routes').then(m => m.PROTOCOL_ROUTES)
          },
          {
            path: 'run',
            loadChildren: () => import('./features/run-protocol/run-protocol.routes').then(m => m.RUN_PROTOCOL_ROUTES)
          },
          {
            path: 'monitor',
            children: [
              {
                path: '',
                loadComponent: () => import('./features/execution-monitor/execution-monitor.component').then(m => m.ExecutionMonitorComponent)
              },
              {
                path: ':id',
                loadComponent: () => import('./features/execution-monitor/components/run-detail.component').then(m => m.RunDetailComponent)
              }
            ]
          },
          {
            path: 'workcell',
            loadChildren: () => import('./features/workcell/workcell.routes').then(m => m.WORKCELL_ROUTES)
          },
          {
            path: 'data',
            loadChildren: () => import('./features/data/data.routes').then(m => m.DATA_ROUTES)
          },
          {
            path: 'settings',
            loadChildren: () => import('./features/settings/settings.routes').then(m => m.SETTINGS_ROUTES)
          },
          {
            path: 'stress-test',
            loadComponent: () => import('./features/stress-test/stress-test.component').then(m => m.StressTestComponent)
          },
          {
            path: 'playground',
            loadComponent: () => import('./features/playground/playground.component').then(m => m.PlaygroundComponent)
          },
          {
            path: 'repl',
            redirectTo: 'playground'
          }
        ]
      },

      // Documentation
      {
        path: 'docs',
        loadChildren: () => import('./features/docs/docs.routes').then(m => m.DOCS_ROUTES)
      }
    ]
  },

  // Legacy/Compatibility Redirects
  { path: 'home', redirectTo: 'app/home' },
  { path: 'assets', redirectTo: 'app/assets' },
  { path: 'protocols', redirectTo: 'app/protocols' },
  { path: 'run', redirectTo: 'app/run' },
  { path: 'workcell', redirectTo: 'app/workcell' },
  { path: 'data', redirectTo: 'app/data' },
  { path: 'settings', redirectTo: 'app/settings' },
  { path: 'stress-test', redirectTo: 'app/stress-test' },
  { path: 'playground', redirectTo: 'app/playground' },

  // Fallback
  { path: '**', redirectTo: '' }
];
