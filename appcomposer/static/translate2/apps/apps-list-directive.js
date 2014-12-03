angular.module("translateApp")
    .directive("acAppsList", function(){
        return {
            restrict: "E",
            templateUrl: "apps/apps-list-directive.html",
            link: function( scope, element, attrs ) {

            }
        }
    });