// Browser mode environment configuration
// Runs entirely in-browser with no backend dependencies
// Uses LocalStorage for persistence and bypasses authentication
export const environment = {
    production: false,
    browserMode: true,  // Pure browser mode - no server required
    apiUrl: '/api/v1',  // Will be intercepted by BrowserModeInterceptor
    wsUrl: '',          // WebSockets disabled in browser mode
    keycloak: {
        enabled: false,
        url: '',
        realm: '',
        clientId: ''
    }
};
