angular
    .module("translateApp")
    .directive("acAppurl", acAppurl);

function acAppurl($location, $log) {
    return {
        restrict: "E",
        templateUrl: "apps/app-url.html",
        scope: {
            appurl: "="
        },
        link: function (scope, element, attr) {

            scope.isValid = isValid;
            scope.calculateUrl = calculateUrl;
            scope.onEnter = onEnter;
            scope.onKey = onKey;

            function calculateUrl(url) {
                return "#/app/" + encodeURIComponent(url);
            } // !calculateUrl

            /**
             * OnEnter redirect.
             */
            function onEnter() {
                $location.path(calculateUrl(scope.url))
            } // !onEnter

            function isValid() {
                var valid = scope.appurlForm.appurl.$valid;
                return valid;
            } // !isValid

        } //! link
    }
}