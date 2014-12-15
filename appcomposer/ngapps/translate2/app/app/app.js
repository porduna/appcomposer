angular
    .module("translateApp")
    .controller("AppCtrl", AppCtrl);


function AppCtrl($scope, $routeParams, $position, $resource) {
    var Appinfo = $resource(APP_DYN_ROOT + "translations/apps/:appurl");
    $scope.params = $routeParams
    $scope.appinfo = Appinfo.get({appurl: "http://www.google.com/app.xml"});

    $scope.test = function() {
        debugger;
    }
}
