angular
    .module("translateApp")
    .directive("acTranslateMe", acTranslateMe);

function acTranslateMe() {
    return {
        restrict: "A",
        link: function(scope, element, attrs) {
            debugger;
        }
    }
}