angular.module("translateApp")
    .controller("AppsCtrl", function ($scope, $resource, DTOptionsBuilder, DTColumnBuilder) {
        $scope.apps = $resource(APP_DYN_ROOT + "translations").query();
    });