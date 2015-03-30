angular
    .module("translateApp")
    .controller("AppCtrl", AppCtrl);


function AppCtrl($scope, $routeParams, $position, $resource) {
    var Appinfo = $resource(APP_DYN_ROOT + "translations/apps/:appurl");
    $scope.params = $routeParams;
    $scope.appurl = $routeParams.appurl;

    $scope.appinfo = Appinfo.get({appurl: $scope.appurl});

    $scope.test = function() {
        debugger;
    }
}
