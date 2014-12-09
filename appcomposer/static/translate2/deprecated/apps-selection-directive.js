angular
    .module("translateApp")
    .directive("acAppsSelection", acAppsSelection);


function acAppsSelection(appsListService, DTOptionsBuilder, DTColumnBuilder) {
    return {
        restrict: "E",
        templateUrl: "apps/apps-selection-directive.html",
        link: function (scope, element, attrs) {

        } // !link
    }; //! return
} //! function