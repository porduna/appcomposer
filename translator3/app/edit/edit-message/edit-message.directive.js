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

    } // !acEditMessageLink
} // !acEditMessage