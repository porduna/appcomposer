angular
    .module("translateApp")
    .directive("acLangTarget", acLangTargetDirective);


function acLangTargetDirective() {
    return {
        restrict: "E",
        templateUrl: "app/translationstab/lang-target/lang-target.directive.html",
        link: langTargetLink,
        controller: 'LangTargetController',
        controllerAs: 'langTargetController',
        scope: {
            appinfo: "=",
            selected: "="
        }
    };


    function langTargetLink(scope, element, attrs, ctrl) {

    } // !langTargetLink
} //! acLangTargetDirective

