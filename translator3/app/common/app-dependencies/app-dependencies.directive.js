angular
    .module("translateApp")
    .directive("acAppDependencies", acAppDependencies);


function acAppDependencies() {
    return {
        restrict: "E",
        controller: "AppDependenciesController",
        controllerAs: "appDependenciesController",
        templateUrl: "common/app-dependencies/app-dependencies.directive.html",
        link: appDependenciesLink,
        scope: {
            dependencies: "=",
            lang: "=",
            target: "="
        }
    };

    /////////////////////
    // IMPLEMENTATIONS
    /////////////////////

    function appDependenciesLink(scope, elem, attrs) {

    } // !appDependenciesLink


} // !acAppDependencies
