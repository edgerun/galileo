const webpack = require('webpack');

module.exports = {
  plugins: [
    new webpack.DefinePlugin({
      $ENV: {
        PRODUCTION: JSON.stringify(process.env.PRODUCTION),
        ENVIRONMENT: JSON.stringify(process.env.ENVIRONMENT),
        GRAFANA_URL: JSON.stringify(process.env.GRAFANA_URL),
        SYMMETRY_URL: JSON.stringify(process.env.SYMMETRY_URL),
        API_URL: JSON.stringify(process.env.API_URL)
      }
    })
  ]
};
