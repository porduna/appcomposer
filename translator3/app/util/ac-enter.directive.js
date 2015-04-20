angular
    .module("translateApp")
    .directive("acEnter", acEnter);


function acEnter() {
    return function (scope, element, attrs) {
        element.bind("keydown keypress", function (event) {
            if (event.which === 13) {
                scope.$apply(function () {
                    scope.$eval(attrs.acEnter);
                });

                event.preventDefault();
            }
        });
    }
}; // !acEnter