angular.module("translateApp")
    .controller("AppsCtrl", function ($scope, $resource, DTOptionsBuilder, DTColumnDefBuilder) {
        $scope.apps = $resource(APP_DYN_ROOT + "translations").query();

        $scope.dt = {};

        debugger;

        $scope.dt.columnDefs = [
            DTColumnDefBuilder.newColumnDef(0).notSortable(),
            DTColumnDefBuilder.newColumnDef(1).notSortable().withOption("width", "40%"),
            DTColumnDefBuilder.newColumnDef(2).notSortable()
        ];

        $scope.dt.options = DTOptionsBuilder.newOptions()
            .withPaginationType('full_numbers')
            .withDisplayLength(2)
            .withOption("autoWidth", true);
    });