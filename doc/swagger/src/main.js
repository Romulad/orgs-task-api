// filepath: /home/romuald/python/portfolio/auth-app/doc/swagger/src/main.js
import SwaggerUI from 'swagger-ui'
import 'swagger-ui/dist/swagger-ui.css';
import spec from './org-open-api.yaml'

const ui = SwaggerUI({
  spec,
  dom_id: '#swagger',
});

ui.initOAuth({
  appName: "Organization Management Platform",
  clientId: 'implicit'
});