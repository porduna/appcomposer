if (window.golab === undefined) {
    window.golab = {};
}

golab = window.golab;

golab.getParameterByName = function(name, url) {
    if (!url) url = window.location.href;
    name = name.replace(/[\[\]]/g, '\\$&');
    var regex = new RegExp('[?&]' + name + '(=([^&#]*)|&|#|$)');
    var results = regex.exec(url);
    if (!results) return null;
    if (!results[2]) return '';
    return decodeURIComponent(results[2].replace(/\+/g, ' '));
}

golab._relative2absolute = function(url, base_url) {
  // https://stackoverflow.com/questions/470832/getting-an-absolute-url-from-a-relative-one-ie6-issue
  var doc      = document
    , old_base = doc.getElementsByTagName('base')[0]
    , old_href = old_base && old_base.href
    , doc_head = doc.head || doc.getElementsByTagName('head')[0]
    , our_base = old_base || doc_head.appendChild(doc.createElement('base'))
    , resolver = doc.createElement('a')
    , resolved_url
    ;
  our_base.href = base_url || '';
  resolver.href = url;
  resolved_url  = resolver.href; // browser magic at work here

  if (old_base) old_base.href = old_href;
  else doc_head.removeChild(our_base);
  return resolved_url;
}

golab.i18n_instance = null;

golab.i18n = function(options) {
    // options:
    //  - endpoint (defaults to https://composer.golabz.eu/)
    //  - language
    //  - standalone (defaults to false)
    //  - debug (defaults to false)

    var self = this;
    golab.i18n_instance = this;

    if (options === null || options === undefined)
        options = {};

    if (options.debug === true) {
        self._debug = true;
    } else {
        self._debug = false;
    }
    if (options.endpoint && options.endpoint.length > 0) {
        self.endpoint = options.endpoint;
    } else {
        self.endpoint = 'https://composer.golabz.eu/translations/v1';
    }
    if (options.avoidMutation === true) {
        self._avoidMutation = true; 
    } else {
        self._avoidMutation = false;
    }

    if (options.standalone === true) {
        self.standalone = true;
    } else {
        var standaloneParameter = golab.getParameterByName("standalone");
        if (standaloneParameter === "true" || standaloneParameter === "1") {
            self.standalone = true;
        } else {
            self.standalone = false;
        }
    }

    function getLanguage() {
        if (options.language !== undefined && options.language !== null)
            return options.language.replace('-', '_');
    
        var langParam = golab.getParameterByName('lang');
        if (langParam != null && langParam.length > 0)
            return langParam.replace('-','_');
        
        if (navigator.language !== null && navigator.language !== undefined) {
            return navigator.language.replace('-','_');
        }
        return 'en';
    }

    this._fullUrl = null;

    var defaultLanguage = 'en_ALL';
    this.language = getLanguage();

    if (this.language.indexOf('_') > 0) {
        this.languageGroup = this.language.split('_')[0];
        this.languageCountry = this.language.split('_')[1];
    } else {
        this.languageGroup = this.language;
        this.languageCountry = 'ALL';
        this.language = this.language + '_ALL';
    }
    this.languageGeneric = this.language.split('_')[0] + '_ALL';

    this._supportedLanguages = [];

    // Only include the messages in those languages that are either English (default)
    // or the current language
    this._allMessages = [
        // {
        //    'url': 'https://.../locales/lang.json'
        //    'lang': 'en_ALL'
        //    'messages': {
        //       'key': 'value',
        //    },
        //    'translation: {
        //       'key': 'value',
        //    }
        // }
    ];

    // Only include the messages in those languages that are either English (default)
    // or the current language
    this._mergedMessages = {
        // lang: {
        //      key: value
        // }
    };
    this._mergedMessages[defaultLanguage] = {};
    this._mergedMessages[this.languageGeneric] = {};
    this._mergedMessages[this.language] = {};

    this._ready = $.Deferred();

    function startIteratingElements() {
        function translateElement(pos, element) {
            var $element = $(element);
            var message = $element.attr('golab-lang');
            if (message !== undefined && message !== null) {
                var translation = golab.i18n_instance.getMessage(message);
                $element.html(translation);
            }
        };

        $("*").each(translateElement);

        if (!self._avoidMutation && window.MutationObserver) {
            function mutationCallback (mutationsList, observer) {
                for(var mutation of mutationsList) {
                    if (typeof mutation.addedNodes == "object") {
                        $(mutation.addedNodes).each(translateElement)
                    }
                }
            }

            var observer = new MutationObserver(mutationCallback);
            observer.observe(document.getElementsByTagName('body')[0], {attributes: false, childList: true, characterData: false, subtree:true});
        }
    }

    function checkPending() {
        var anyPendingHolder = {
            anyPending: false
        };

        $(self._allMessages).each(function (pos, obj) {
            if (obj.pendingMessages || obj.pendingTranslation) {
                anyPendingHolder.anyPending = true;
            }
        });

        if (anyPendingHolder.anyPending)
            return;

        // Resolve
        if (self._debug)
            console.log('AppComposer ready');

        self._ready.resolve();

        startIteratingElements();
    }

    $("meta[name='translations']").each(function(position, metaObject) {
        $metaObject = $(metaObject);
        var lang = $metaObject.attr('lang');
        if (lang == null || lang === undefined || lang.length == 0)
            lang = 'en_ALL';

        var country;
        if (lang.indexOf('_') > 0) {
            var pieces = lang.split('_');
            lang = pieces[0];
            country = pieces[1];
        } else {
            var country = $metaObject.attr('country');
            if (!country)
                country = 'ALL';
        }
        var currentLanguage = lang + '_' + country;

        // if self.language is es_PE, I am interested in es_PE (currentLanguage), es_ALL (languageGeneric) and en_ALL (default).
        // Everything else I don't care
        if (currentLanguage != defaultLanguage && currentLanguage != self.language && currentLanguage != self.languageGeneric) {
            // Ignore other message files
            if (self._debug)
                console.log("Ignoring ", metaObject);
            return;
        }
        
        var url = $metaObject.attr('value');
        if (url === undefined) {
            console.log('meta', metaObject, 'does not have value');
            return;
        }
        var fullUrl = golab._relative2absolute(url);
        if (lang === 'en_ALL' && self._fullUrl == null) {
            self._fullUrl = fullUrl;
        }
        var currentRecord = {
            url: fullUrl,
            lang: currentLanguage,
            messages: {},
            translations: {},
            pendingMessages: true,
            pendingTranslation: true
        };
        self._allMessages.push(currentRecord);

        $.get(fullUrl).done(function(messages, textStatus, jqXHR) {

            if (jqXHR.responseXML) {
                currentRecord.messages = {};

                $(messages).find('msg').each(function (pos, message) {
                    var key = $(message).attr('name');
                    var value = $(message).html();
                    currentRecord.messages[key] = value;
                    var currentStore = self._mergedMessages[currentRecord.lang];
                    currentStore[key] = value;
                });
            }

            if (jqXHR.responseJSON) {
                if (messages !== undefined && messages.messages !== undefined) {
                    currentRecord.messages = messages.messages;
                    $(messages.messages).each(function (pos, message) {
                        var currentStore = self._mergedMessages[currentRecord.lang];
                        if (message.key !== undefined) 
                            currentStore[message.key] = message.value;
                    });
                }
            }
        }).always(function () {
            currentRecord.pendingMessages = false;
            checkPending();
        });

        var currentEndpoint = self.endpoint + '/' + self.language + '/' + fullUrl;

        // if the self.language is English; don't contact app composer at all (no translation needed)
        // also, if the current language is not English, don't contact it
        if (self.language !== defaultLanguage && currentLanguage === defaultLanguage) {
            $.get(currentEndpoint)
                .done(function (messages) {
                    currentRecord.translations = messages;
                    for (var key in messages) {
                        var currentStore = self._mergedMessages[self.language];
                        currentStore[key] = messages[key];
                    };
                })
                .always(function () {
                    currentRecord.pendingTranslation = false;
                    checkPending();
                });
        } else {
            currentRecord.pendingTranslation = false;
        }
    });

    this.ready = function(handler) {
        self._ready.done(handler);
    }

    this.getLanguages = function() {    
        var response = $.Deferred();
        $.get(fullUrl).done(function(contents) {
            response.done(contents.languages);
        }
        return response;
    }

    this.getMessage = function(key) {
        if (self._mergedMessages[self.language][key] !== undefined)
            return self._mergedMessages[self.language][key];
        if (self._mergedMessages[self.languageGeneric][key] !== undefined)
            return self._mergedMessages[self.languageGeneric][key];
        if (self._mergedMessages[defaultLanguage][key] !== undefined)
            return self._mergedMessages[defaultLanguage][key];
        return null;
    }
}

golab._checkAutoLoad = function () {
    $(document).ready(function () {
        if (golab.i18n_instance !== null)
            return;

        var autoload = $("meta[name='golab-i18n-autoload'")[0];
        if (autoload !== undefined && $(autoload).attr('value') === 'true') {
            var new_instance = new golab.i18n();
        }
    });
}

if (typeof jQuery == 'undefined') {
    console.log('jQuery not found before GoLab i18n');
    var script = document.createElement('script');
    script.type = "text/javascript";
    script.src = "https://ajax.googleapis.com/ajax/libs/jquery/1.11.0/jquery.min.js";
    script.onload = golab._checkAutoLoad;
    document.getElementsByTagName('head')[0].appendChild(script);
} else {
    $(document).ready(function() {
        golab._checkAutoLoad();
    });
}


