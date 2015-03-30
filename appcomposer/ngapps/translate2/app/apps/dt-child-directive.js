/** So far, not working */

angular
    .module("translateApp")
    .directive("dtChild", dtChild);


function dtChild() {
    return {
        restrict: "E",
        transclude: true,
        link: function (scope, element, attrs) {

        } // !link
    }; //! return
} //! function