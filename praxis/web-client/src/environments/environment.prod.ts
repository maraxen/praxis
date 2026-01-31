// Production environment configuration
export const environment = {
  production: true,
  apiUrl: '/api/v1',
  wsUrl: `ws://${window.location.host}/api/v1/ws`,
  keycloak: {
    url: '/auth', // Production Keycloak URL (behind proxy)
    realm: 'praxis',
    clientId: 'praxis'
  }
};
