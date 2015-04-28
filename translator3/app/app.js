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
        JQT_PAG_LAST: "Last",

        // app
        PREVIEW: "Preview",
        COULD_NOT_LOAD_APP: "Unfortunately, it was not possible to load the specified application.",
        INVALID_APP: "The application might be invalid or not exist, or there could be a server or network error. You may try again later, or translate a different application.",
        BACK_TO_APPS_LIST: "Go back to the Applications List",
        ERROR_IS: "The error is:",
        HTTP_CODE: "HTTP code:",
        MESSAGE: "Message:",
        DETAILS: "Details:",
        EDIT_TRANSLATION: "Edit Translation",
        PLEASE_CHOOSE_LANG: "Please, choose a language.",
        A_URL: "URL",
        NOT_AVAIL: "N/A",
        CREATED: "Created:",
        LAST_MODIFIED: "Last modified:",
        TRANSLATED: "Translated:",

        // app/lang-target
        LANGUAGE: "Language:",
        SELECT_LANG: "Select a language",

        // edit
        BACK: "Back",
        ERROR_LOADING: "Unfortunately, it was not possible to load the specified application or translation.",
        APP_MAYBE_INVALID: "The application might be invalid or not exist, or there could be a server or network error. You may try again later, or translate a different application.",
        TRANS_NOT_INSTANT: "The translation will not be applied instantly",
        TRANS_NOT_INSTANT_MESSAGE: "Thank you for translating this application! Please note that though you can translate this application and it will be saved as you go, the translation will need to be applied by the original application developer before the changes take effect, so it may take a while.",
        LOADING_PLEASE_WAIT: "Loading. Please, wait...",

        // edit/message
        MESSAGE_PROVIDED: "This message translation is provided by the App and cannot be modified",
        COULDNT_SAVE: "Could not save the last changes.",
        SUGGESTED_AUTOMATIC_TRANSLATIONS: "Suggested automatic translations:",
        RECENTLY_ACTIVE: "Recently active:",









    });
    $translateProvider.translations('de', {
        TITLE: 'Hallo',
        FOO: 'Dies ist ein Paragraph.',
        BUTTON_LANG_EN: 'englisch',
        BUTTON_LANG_DE: 'deutsch'
    });

    $translateProvider.preferredLanguage('en');

} // !translateProviderConfig
