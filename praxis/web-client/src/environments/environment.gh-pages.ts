// Browser mode environment configuration for GitHub Pages deployment
// This environment runs entirely client-side without backend dependencies
export const environment = {
    production: false,
    browserMode: true,  // Enable browser mode - uses mock data and bypasses auth
    apiUrl: '/api/v1',  // Will be intercepted by BrowserModeInterceptor
    wsUrl: '',  // WebSockets disabled in browser mode
    keycloak: {
        // Keycloak is disabled in browser mode
        enabled: false,
        url: '',
        realm: '',
        clientId: ''
    }
};
