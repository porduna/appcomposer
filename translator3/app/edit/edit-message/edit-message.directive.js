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

        var input = elem.find("input");

        scope.setCurrentTextValue = setCurrentTextValue;
        scope.getCurrentTextValue = getCurrentTextValue;
        scope.getModelController = getModelController;
        scope.focusTextInput = focusTextInput;

        function getCurrentTextValue() {
            return input.val();
        } // !getCurrentTextValue

        function setCurrentTextValue(val) {
            input.val(val);
        } // !setCurrentTextValue


        function getModelController() {
            return input.data('$ngModelController');
        }

        function focusTextInput() {
            input.focus();
        }

    } // !acEditMessageLink

} // !acEditMessage