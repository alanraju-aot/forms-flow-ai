if (window.location.href.startsWith("https://test-")) {
  document.querySelector("[cam-widget-header]").style.backgroundColor = "orange";
} else if (window.location.href.startsWith("https://dev-")) {
  document.querySelector("[cam-widget-header]").style.backgroundColor = "green";
} else if (window.location.href.startsWith("http://localhost")) {
  document.querySelector("[cam-widget-header]").style.backgroundColor = "grey";
}

window.camAdminConf = {
  customScripts: {
    // AngularJS module names
    ngDeps: ['custom-logout'],
    // RequireJS configuration for a complete configuration documentation see:
    // http://requirejs.org/docs/api.html#config
    deps: ['jquery', 'custom-logout'],
    paths: {
      'custom-logout': 'custom/logout'
    }
  },

  app: {
    name: 'Process Engine',
    vendor: ' '
  }
};

export default {
    customScripts: [
        'custom/logout',
		//UNCOMMENT FOR JWT AUTH '../identity-keycloak/scripts/identity-keycloak-auth.js'
    ]
};