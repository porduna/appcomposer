angular
    .module("translateApp")
    .directive("acEditMessage", acEditMessage);


function acEditMessage() {

    return {
        restrict: "E",
        templateUrl: 'edit/edit-message/edit-message.directive.html',
        link: acEditMessageLink,
        controller: 'EditMessageController',
        controllerAs: 'editMessageController',
        scope: {
            bundle: "=bundle",
            key: "=key",
            item: "=item"
        }
    };

    function acEditMessageLink(scope, elem, attrs, ctrl) {

        var input = elem.find("input.ac-edit-message-input");

        scope.setCurrentTextValue = setCurrentTextValue;
        scope.getCurrentTextValue = getCurrentTextValue;
        scope.getModelController = getModelController;
        scope.focusTextInput = focusTextInput;
        scope.flashElement = flashElement;

        // ---------------
        // Implementations
        // ---------------

        /**
         * Flashes the input element to show that it has changed. We do it in jQuery because
         * it seems to be much easier than with ngAnimate or similar.
         */
        function flashElement () {
            var elements = input;

            var initialBackground = $(elements).css("background");
            var opacity = 100;
            var color = "255, 255, 20"; // has to be in this format since we use rgba
            var interval = setInterval(function () {
                opacity -= 3;
                if (opacity <= 0)
                {
                    clearInterval(interval);
                    $(elements).css({background: initialBackground});
                    return;
                }
                $(elements).css({background: "rgba(" + color + ", " + opacity / 100 + ")"});
            }, 30)
        }

        function getCurrentTextValue() {
            return input.val();
        } // !getCurrentTextValue

        function setCurrentTextValue(val) {
            input.val(val);
        } // !setCurrentTextValue


        function getModelController() {
            return input.data('$ngModelController');
        } // !getModelController

        function focusTextInput() {
            if ($(input).is(':focus') == false) {
                input.focus();
            }
        } // !focusTextInput

    } // !acEditMessageLink

} // !acEditMessage