angular
    .module("translateApp")
    .directive("acAppurl", acAppurl);

function acAppurl($location, $log) {
    return {
        restrict: "E",
        templateUrl: "apps/appurl.directive.html",
        scope: {
            appurl: "="
        },
        link: function (scope, element, attr) {

            scope.isValid = isValid;
            scope.calculateUrl = calculateUrl;
            scope.onEnter = onEnter;

            function calculateUrl(url) {
                return "#/app/" + encodeURIComponent(url);
            } // !calculateUrl

            /**
             * OnEnter redirect.
             */
            function onEnter() {
                // TODO: Check whether the URL is valid.

                if(scope.url != undefined && scope.url != "") {
                    var url = calculateUrl(scope.url);

                    // Remove the starting dash.
                    url = url.replace(/^#+|#+$/gm, '');

                    $location.path(url);
                }
            } // !onEnter

            function isValid(form) {
                if(form == undefined)
                    return false;
                var valid = form.appurl.$valid;
                return valid;
            } // !isValid

        } //! link
    }
}