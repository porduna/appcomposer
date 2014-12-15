angular
    .module("translateApp")
    .directive("acAppDetails", acAppDetails);


function acAppDetails() {
    return {
        restrict: "E",
        templateUrl: "apps/app-details.html",
        scope: {
            app: "=app"
        },
        link: function (scope, element, attrs) {
        } // !link
    }; //! return
} //! function