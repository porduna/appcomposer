angular
    .module("translateApp")
    .controller("PreviewTabCtrl", PreviewTabCtrl);


function PreviewTabCtrl($scope) {
    SHINDIG_SERVER = 'http://shindig.epfl.ch';
    RELATIVE_URL = '/gadgets/ifr?nocache=1&url=';
}