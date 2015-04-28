angular
    .module('translateApp', [
        'ngRoute',
        'ngResource',
        'ngSanitize',
        'ui.bootstrap',
        'ui.select',
        'ui.utils',
        'datatables',
        'truncate',
        'selectionModel',
        'ui.bootstrap.modal',
        'pascalprecht.translate',
        'ui.gravatar'
    ])
    .config(['$routeProvider', '$compileProvider', '$translateProvider', configFunc])
    .run(['$log', '$location', initialize]);

function initialize($log, $location) {
    $log.debug("INITIALIZING...");

    var src = window.location.origin + window.location.pathname;

    if (src.search("http://localhost:9000") == 0 || src.search("http://localhost:5000") == 0)
        window.APP_DYN_ROOT = "http://localhost:5000/translator/";
    else {

        // !!!! WARNING !!!!
        // This assumes we serve the production API from whatever/ and the statics from /whatever/web.
        src = src.split('/');
        src.pop();
        src.pop();
        src = src.join('/');

        window.APP_DYN_ROOT = src + '/';
    }

} // !initialize

function configFunc($routeProvider, $compileProvider, $translateProvider) {
    $routeProvider
        .when('/apps', {
            templateUrl: 'apps/apps.html',
            controller: 'AppsController'
        })
        .when('/app/:appurl*', {
            templateUrl: 'app/app.html',
            controller: 'AppController'
        })
        .when('/edit/:targetlang/:targetgroup/:appurl*', {
            templateUrl: 'edit/edit.html',
            controller: 'EditController'
        })
        .otherwise({
            redirectTo: '/apps'
        });

    $compileProvider.aHrefSanitizationWhitelist(/^\s*(https?|ftp|mailto):/);

    $translateProvider.translations('en', {
        // apps
        TITLE: "Title",
        DESCRIPTION: "Description",
        TRANSLATIONS: "Translations",
        CHOOSE_APP_TRANSLATE: "Choose an application to translate: ",
        APPS_LIST: " Applications List",

        // apps/app-details
        FULL_NAME: "Full Name: ",
        XML_URL: "XML URL: ",
        SOURCE: "Source: ",
        TRANSLATE: "Translate",

        // apps/appurl
        CUSTOM_APP_URL: "Custom application URL",
        DEVS_ONLY_WARNING: "This will generally be required by developers only. Most users should choose an application from the Applications List above.",
        URL: "URL: ",
        APP_URL: "URL of the app",
        PLEASE_PROVIDE_URL: "Please, provide the URL for the custom application",

        // apps/"jquery-table"
        JQT_SEARCH: "Search:",
        JQT_PROCESSING: "Processing...",
        JQT_INFO: "Showing page _PAGE_ of _PAGES_",
        JQT_LEN: "Display _MENU_ records per page",
        JQT_ZERO: "Nothing found",
        JQT_INFOEMPTY: "No records available",
        JQT_INFOFILTERED: "(filtered from _MAX_ total records)",
        JQT_PAG_FIRST: "First",
        JQT_PAG_PREV: "Previous",
        JQT_PAG_NEXT: "Next",
        JQT_PAG_LAST: "Last"
    });
    $translateProvider.translations('de', {
        TITLE: 'Hallo',
        FOO: 'Dies ist ein Paragraph.',
        BUTTON_LANG_EN: 'englisch',
        BUTTON_LANG_DE: 'deutsch'
    });

    $translateProvider.preferredLanguage('en');

} // !translateProviderConfig
