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
        'selectionModel'
    ])
    .config(['$routeProvider', routeConfig], ['$compileProvider', compileProviderConfig])
    .controller('TranslateCtrl', function ($scope, $rootScope) {
        $rootScope.objectKeys = Object.keys;
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
        .when('/edit/:appurl*', {
            templateUrl: 'edit/edit.html',
            controller: 'EditCtrl'
        })
        .otherwise({
            redirectTo: '/apps'
        });
}


function compileProviderConfig($compileProvider) {
    $compileProvider.aHrefSanitizationWhitelist(/^\s*(https?|ftp|mailto):/);
}
