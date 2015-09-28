var appList = angular.module('appList', []);
appList.controller('AppListCtrl', function ($scope) {
    $scope.apps = [];
    $scope.APP_FORMATS = FORMATS;
    $scope.encodeURIComponent = encodeURIComponent;
    $.ajax({
      url: APPS_URL,
      success: function (obj) {
        $scope.$apply(function(scope) {
            $.each(obj.apps, function( pos, appset ){
                $.each(appset.apps, function (pos, app) {
                    console.log(app);
                    var d = new Date(app.last_change.replace(/ /, 'T'));
                    app.last_change = d.getFullYear() + "-" + zfill(d.getMonth() + 1) + "-" + zfill(d.getDate()) + " " + zfill(d.getHours()) + ":" + zfill(d.getMinutes()) + ":" + zfill(d.getSeconds());
                });
            });

            scope.apps = obj.apps;
        });
      },
      dataType: "json"
    });
});

function zfill(n) {
    if (n < 10) 
        return "0" + n;
    return n;
}

