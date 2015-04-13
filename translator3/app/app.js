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
    .config(['$routeProvider', routeConfig], ['$compileProvider', compileProviderConfig]);


function routeConfig($routeProvider) {
    $routeProvider
        .when('/apps', {
            templateUrl: 'apps/apps.html',
            controller: 'AppsCtrl'
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
