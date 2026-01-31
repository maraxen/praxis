// Development environment configuration
export const environment = {
  production: false,
  browserMode: true,  // Default to browser mode until production mode is stabilized
  apiUrl: '/api/v1',
  wsUrl: 'ws://localhost:8000/api/v1/ws',
  keycloak: {
    url: 'http://localhost:8080',
    realm: 'praxis',
    clientId: 'praxis'
  }
};
