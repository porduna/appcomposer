angular
    .module("translateApp")
    .directive("acAppsFilter", acAppsFilter);


function acAppsFilter() {

    return {
        restrict: "E",
        templateUrl: "apps/apps-filter/apps-filter.directive.html",
        controller: "AppsFilterController",
        controllerAs: "appsFilterController",
        link: acAppsFilterLink,
        scope: {

        }
    };

    // ---------------
    // Implementations
    // ---------------

    function acAppsFilterLink() {

    } // !acAppsFilterLink

} // !acAppsFilter