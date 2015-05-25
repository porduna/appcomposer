var appList = angular.module('appList', []);
appList.controller('AppListCtrl', function ($scope) {
    $scope.apps = [];
    $scope.APP_FORMATS = FORMATS;
    $.ajax({
      url: APPS_URL,
      success: function (obj) {
        $scope.$apply(function(scope) {
           scope.apps = obj.apps;
        });
      },
      dataType: "json"
    });
});

