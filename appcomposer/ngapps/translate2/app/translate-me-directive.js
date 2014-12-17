angular
    .module("translateApp")
    .directive("acTranslateMe", acTranslateMe);

function acTranslateMe($filter) {
    return {
        restrict: "A",
        transclude: false,
        link: function(scope, element, attrs) {
            var originalText = element.text();
            var newText = $filter("translate")(originalText);

            // This is easier but it is commented out because it removes child elements while setting the new text.
            // This is inconvenient for icons.
            // element.text(newText);

            // Replace *only* the text elements with the translation.
            element.contents().filter(function(){ return this.nodeType == 3; }).replaceWith(newText);
        }
    }
}