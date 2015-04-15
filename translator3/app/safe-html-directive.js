angular
    .module("translateApp")
    .directive("acSafeHtml", acSafeHtml);

function acSafeHtml($sanitize, $filter) {
    return {
        restrict: "A",
        link: function(scope, element, attr) {
            debugger;
            // No actual binding.
            var orig = scope.$eval(attr.acSafeHtml);
            var safe = $sanitize(orig);
            var safeWithLinks = createAnchors(safe);
            element.html(safeWithLinks);
        }
    }
}

/**
 * The createAnchors function turns raw http:// links in text into html.
 * It is thus somewhat similar to ngSanitize's linky.
 * @param text
 * @returns {*}
 */
function createAnchors(text) {
    return text.replace(/(http[^\s]+)/, '<a href="$1">$1</a>');
}