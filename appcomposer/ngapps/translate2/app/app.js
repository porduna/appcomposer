angular
    .module('translateApp', [
        'ngRoute',
        'ngResource',
        'ngSanitize',
        'datatables',
        'truncate'
    ])
    .config(['$routeProvider', routeConfig], ['$compileProvider', compileProviderConfig])
    .controller('TranslateCtrl', function ($scope) {

    });


function routeConfig($routeProvider) {
    $routeProvider
        .when('/apps', {
            templateUrl: 'apps/apps.html',
            controller: 'AppsCtrl'
        })
        .when('/app/:appurl*', {
            templateUrl: 'app/app.html',
            controller: 'AppCtrl'
        })
        .otherwise({
            redirectTo: '/apps'
        });
}


function compileProviderConfig($compileProvider) {
    $compileProvider.aHrefSanitizationWhitelist(/^\s*(https?|ftp|mailto):/);
}
