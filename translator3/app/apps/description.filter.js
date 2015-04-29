angular
    .module("translateApp")
    .filter("descriptionFilter", descriptionFilter);


function descriptionFilter() {
    return function(text) {
        return text;
    }
}