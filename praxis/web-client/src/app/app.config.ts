import { ApplicationConfig, provideBrowserGlobalErrorListeners, APP_INITIALIZER } from '@angular/core';
import { provideRouter, withComponentInputBinding, withInMemoryScrolling, RouteReuseStrategy } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideHttpClient, withInterceptors, HttpRequest, HttpHandlerFn, HttpClient } from '@angular/common/http';
import { provideMarkdown } from 'ngx-markdown';
import { inject } from '@angular/core';
import { routes } from './app.routes';
import { PlaygroundRouteReuseStrategy } from './features/playground/playground-route-reuse.strategy';
import { errorInterceptor } from './core/http/error.interceptor';
import { browserModeInterceptor } from './core/interceptors/browser-mode.interceptor';
import { importProvidersFrom } from '@angular/core';
import { FormlyModule } from '@ngx-formly/core';
import { FormlyMaterialModule } from '@ngx-formly/material';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { AssetSelectorComponent } from './shared/formly-types/asset-selector.component';
import { RepeatTypeComponent } from './shared/formly-types/repeat-section.component';
import { ChipsTypeComponent } from './shared/formly-types/chips.component';
import { IndexSelectorFieldComponent } from './shared/formly-types/index-selector-field.component';
import { DictInputComponent } from './shared/formly-types/dict-input.component';
import { KeycloakService } from './core/auth/keycloak.service';
import { KeyboardService } from './core/services/keyboard.service';
import { ModeService } from './core/services/mode.service';
import { CustomIconRegistryService } from './core/services/custom-icon-registry.service';
import { from, switchMap } from 'rxjs';

/**
 * Initialize Keycloak on app startup (skipped in browser mode)
 */
function initializeKeycloak(keycloakService: KeycloakService) {
  return () => {
    return keycloakService.init({ onLoad: 'check-sso' });
  };
}

/**
 * Initialize Keyboard shortcuts and Command Palette
 */
function initializeKeyboard(keyboardService: KeyboardService) {
  return () => Promise.resolve();
}

function initializeIcons(iconRegistryService: CustomIconRegistryService) {
  return () => iconRegistryService.init();
}

/**
 * HTTP interceptor that adds Keycloak Bearer token to requests (skipped in browser modes)
 */
const keycloakInterceptor = (req: HttpRequest<unknown>, next: HttpHandlerFn) => {
  const modeService = inject(ModeService);

  // Skip token in browser modes
  if (modeService.isBrowserMode()) {
    return next(req);
  }

  const keycloakService = inject(KeycloakService);

  // Skip token for non-API requests (exclude assets)
  if (!req.url.includes('/api/') || req.url.includes('assets/')) {
    return next(req);
  }

  // Get token and add to request
  return from(keycloakService.getToken()).pipe(
    switchMap(token => {
      if (token) {
        const clonedReq = req.clone({
          setHeaders: {
            Authorization: `Bearer ${token}`
          }
        });
        return next(clonedReq);
      }
      return next(req);
    })
  );
};

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes, withComponentInputBinding(), withInMemoryScrolling({ anchorScrolling: 'enabled', scrollPositionRestoration: 'enabled' })),
    provideAnimationsAsync(),
    // Browser Mode interceptor runs FIRST to catch API requests before they hit proxy
    provideHttpClient(withInterceptors([browserModeInterceptor, keycloakInterceptor, errorInterceptor])),
    // Keep playground component alive during navigation (preserves JupyterLite kernel)
    { provide: RouteReuseStrategy, useClass: PlaygroundRouteReuseStrategy },
    provideMarkdown({
      loader: HttpClient,
      mermaid: true
    } as any),
    {
      provide: APP_INITIALIZER,
      useFactory: initializeKeycloak,
      deps: [KeycloakService],
      multi: true
    },
    {
      provide: APP_INITIALIZER,
      useFactory: initializeKeyboard,
      deps: [KeyboardService],
      multi: true
    },
    {
      provide: APP_INITIALIZER,
      useFactory: initializeIcons,
      deps: [CustomIconRegistryService],
      multi: true
    },
    importProvidersFrom(
      MatSnackBarModule,
      FormlyModule.forRoot({
        types: [
          { name: 'asset-selector', component: AssetSelectorComponent },
          { name: 'chips', component: ChipsTypeComponent },
          { name: 'repeat', component: RepeatTypeComponent },
          { name: 'index-selector', component: IndexSelectorFieldComponent },
          { name: 'dict-input', component: DictInputComponent },
        ],
        wrappers: [
          // { name: 'section', component: SectionWrapperComponent }
        ],
        validationMessages: [
          { name: 'required', message: 'This field is required' },
          { name: 'min', message: 'Value should be greater than or equal to minimum' },
          { name: 'max', message: 'Value should be less than or equal to maximum' },
          { name: 'minLength', message: 'Minimum length is required' },
          { name: 'maxLength', message: 'Maximum length exceeded' },
          { name: 'pattern', message: 'Value does not match required pattern' },
        ],
      }),
      FormlyMaterialModule
    )
  ]
};
