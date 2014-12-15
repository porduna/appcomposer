angular
    .module("translateApp")
    .directive("acTranslateMe", acTranslateMe);

function acTranslateMe($filter) {
    return {
        restrict: "A",
        link: function(scope, element, attrs) {
            var originalText = element.text();
            var newText = $filter("translate")(originalText);
            element.text(newText);
        }
    }
}