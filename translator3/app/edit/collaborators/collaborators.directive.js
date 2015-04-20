angular
    .module("translateApp")
    .directive("acCollaborators", acCollaborators);


function acCollaborators() {
    return {
        restrict: "E",
        templateUrl: "edit/collaborators/collaborators.directive.html",
        link: acCollaboratorsLink,
        controller: "CollaboratorsController",
        controllerAs: "collaboratorsController",
        scope: {

        }
    }; // !return

    function acCollaboratorsLink(scope, elem, attrs, ctrl) {

    } // !acCollaboratorsLink

} //! acCollaborators