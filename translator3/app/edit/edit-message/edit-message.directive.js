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

        scope.getCurrentTextValue = getCurrentTextValue;
        scope.getModelController = getModelController;

        function getCurrentTextValue() {
            return input.val();
        } // !getCurrentTextValue


        function getModelController() {
            return input.data('$ngModelController');
        }

    } // !acEditMessageLink
} // !acEditMessage