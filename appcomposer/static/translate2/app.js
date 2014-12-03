angular
    .module('translateApp', [
        'ngRoute'
    ])
    .config(['$routeProvider', function($routeProvider){
        $routeProvider
            .when('/apps', {
                templateUrl: 'apps/apps.html',
                controller: 'AppsCtrl'
            })
            .otherwise({
                redirectTo: '/apps'
            });
    }])
    .controller('TranslateCtrl', function($scope){

    });
