angular
    .module("translateApp")
    .directive("acCollaborator", acCollaborator);


function acCollaborator() {
    return {
        restrict: "E",
        templateUrl: "edit/collaborators/collaborator/collaborator.directive.html",
        controller: "CollaboratorController",
        controllerAs: "CollaboratorsController",
        scope: {}
    };

    function acCollaboratorLink(scope, elem, attrs, ctrl) {

    } // !acCollaboratorLink

} // !acCollaborator