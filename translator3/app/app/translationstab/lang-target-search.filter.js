angular
    .module('translateApp')
    .filter('langTargetSearchFilter', langTargetSearchFilter);


/**
 * This is a custom filter so that the search in the angular-ui select2 can work properly for the languages.
 * @returns {filter}
 */
function langTargetSearchFilter() {
    return filter;

    function filter(input, search, all_langs) {
        search = search.toLowerCase();
        var filtered = [];
        angular.forEach(input, function (value, index) {
            var elementText = all_langs[value].toLowerCase();
            if (elementText.indexOf(search) != -1)
                filtered.push(value);
        });
        return filtered;
    } // !filter

} // !langTargetSearchFilter