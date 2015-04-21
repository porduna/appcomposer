angular
    .module('translateApp', [
        'ngRoute',
        'ngResource',
        'ngSanitize',
        'ui.bootstrap',
        'ui.select',
        'ui.utils',
        'datatables',
        'truncate',
        'selectionModel',
        'ui.bootstrap.modal'
    ])
    .config(['$routeProvider', routeConfig], ['$compileProvider', compileProviderConfig])
    .run(['$log', '$location', initialize]);

function initialize($log, $location) {
    $log.debug("INITIALIZING...");

    var src = window.location.origin + window.location.pathname;

    if(src.search("http://localhost:9000") == 0 || src.search("http://localhost:5000") == 0)
        window.APP_DYN_ROOT = "http://localhost:5000/translator/";
    else {

        // !!!! WARNING !!!!
        // This assumes we serve the production API from whatever/ and the statics from /whatever/web.
        src = src.split('/');
        src.pop();
        src.pop();
        src = src.join('/');

        window.APP_DYN_ROOT = src + '/';
    }

} // !initialize

function routeConfig($routeProvider) {
    $routeProvider
        .when('/apps', {
            templateUrl: 'apps/apps.html',
            controller: 'AppsController'
        })
        .when('/app/:appurl*', {
            templateUrl: 'app/app.html',
            controller: 'AppController'
        })
        .when('/edit/:targetlang/:targetgroup/:appurl*', {
            templateUrl: 'edit/edit.html',
            controller: 'EditController'
        })
        .otherwise({
            redirectTo: '/apps'
        });
}


function compileProviderConfig($compileProvider) {
    $compileProvider.aHrefSanitizationWhitelist(/^\s*(https?|ftp|mailto):/);
}
