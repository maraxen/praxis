// Production environment configuration
export const environment = {
  production: true,
  baseHref: '/',
  apiUrl: '/api/v1',
  wsUrl: `ws://${window.location.host}/api/v1/ws`,
  pyodideSnapshotVersion: 'v1.0.0',
  defaultDeckType: 'pylabrobot.resources.hamilton.HamiltonSTARDeck',
  keycloak: {
    url: '/auth', // Production Keycloak URL (behind proxy)
    realm: 'praxis',
    clientId: 'praxis'
  }
};
