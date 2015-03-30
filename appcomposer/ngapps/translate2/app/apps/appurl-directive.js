angular
    .module("translateApp")
    .directive("acAppurl", acAppurl);

function acAppurl() {
    return {
        restrict: "E",
        templateUrl: "apps/app-url.html",
        scope: {
            appurl: "="
        },
        link: function (scope, element, attr) {

            scope.isValid = isValid;

            function isValid() {
                var valid = scope.appurlForm.appurl.$valid;
                return valid;
            }

        } //! link
    }
}