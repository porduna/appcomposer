angular.module("translateApp")
    .controller("AppsCtrl", function ($scope, $resource, DTOptionsBuilder, DTColumnDefBuilder) {
        $scope.apps = $resource(APP_DYN_ROOT + "translations").query();

        $scope.dt = {};

        $scope.dt.columnDefs = [
            DTColumnDefBuilder.newColumnDef(0).notSortable(),
            DTColumnDefBuilder.newColumnDef(1).notSortable(),
            DTColumnDefBuilder.newColumnDef(2).notSortable()
        ];

        $scope.dt.options = DTOptionsBuilder.newOptions().withPaginationType('full_numbers').withDisplayLength(2);
    });