angular
    .module('translateApp', [
        'ngRoute'
    ])
    .config(['$routeProvider', routeConfig])
    .controller('TranslateCtrl', function ($scope) {

    });


function routeConfig($routeProvider) {
    $routeProvider
        .when('/apps', {
            templateUrl: 'apps/apps.html',
            controller: 'AppsCtrl'
        })
        .otherwise({
            redirectTo: '/apps'
        });
}
