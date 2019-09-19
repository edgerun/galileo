export const environment = {
  production: $ENV.PRODUCTION === 'true',
  environment: $ENV.ENVIRONMENT,
  apiUrl: $ENV.API_URL,
  symmetryUrl: $ENV.SYMMETRY_URL,
  grafanaUrl: $ENV.GRAFANA_URL,
};
