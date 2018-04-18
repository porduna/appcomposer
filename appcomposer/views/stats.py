import sys
import json
import hashlib
import operator
import datetime
import urlparse

import requests

from collections import defaultdict

from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from flask import Blueprint, render_template, request, url_for, jsonify

from appcomposer.db import db
from appcomposer.models import TranslatedApp, TranslationUrl, TranslationBundle, RepositoryApp, GoLabOAuthUser, ActiveTranslationMessage, TranslationMessageHistory
from appcomposer.models import TranslationExternalSuggestion, RepositoryAppCheckUrl
from appcomposer.login import requires_golab_login

from appcomposer.utils import public
from appcomposer.languages import LANGUAGE_NAMES_PER_CODE, LANGUAGE_THRESHOLD, ALL_LANGUAGES, get_locale_english_name
from appcomposer.translator.suggestions import microsoft_translator, google_translator, deepl_translator

translator_stats_blueprint = Blueprint('translator_stats', __name__, static_folder = '../../translator3/dist/', static_url_path = '/web')

@translator_stats_blueprint.route('/')
@public
def stats():
    return render_template("translator/stats.html")

@translator_stats_blueprint.route('/status')
@public
def stats_status():
    translations_per_languages = db.session.query(
            func.count(ActiveTranslationMessage.id),
            TranslationBundle.language
        ).filter(
                ActiveTranslationMessage.taken_from_default == False, 
                ActiveTranslationMessage.from_developer == False,
                ActiveTranslationMessage.bundle_id == TranslationBundle.id,
                ActiveTranslationMessage.same_tool.in_([True, None]),
                TranslationBundle.target == 'ALL',
                TranslationBundle.translation_url_id == TranslationUrl.id,
                TranslatedApp.translation_url_id == TranslationUrl.id,
                RepositoryApp.url == TranslatedApp.url,
            ).group_by(TranslationBundle.language).all()
    translations_per_languages = list(translations_per_languages)
    translations_per_languages.sort(lambda (n1, lang1), (n2, lang2):  cmp(n1, n2), reverse=True)

    total = sum([ count for count, lang in translations_per_languages ])

    lang_codes = [ lang + '_ALL' for count, lang in translations_per_languages if lang.split('_')[0] in LANGUAGE_NAMES_PER_CODE and lang.split('_')[0] != 'en' ]

    translations_per_languages = [(count, LANGUAGE_NAMES_PER_CODE[lang.split('_')[0]] ) for count, lang in translations_per_languages if lang.split('_')[0] in LANGUAGE_NAMES_PER_CODE and lang.split('_')[0] != 'en' ]

    data_per_language = defaultdict(list)
        # language: [
        #     {
        #         'name' : "Name of app",
        #         'thumb' : "link to thumb",
        #         'percent': 0.5
        #     }
        # ]
    
    total_apps = db.session.query(RepositoryApp).filter_by(translatable = True).count()

    for repository_app in db.session.query(RepositoryApp).filter_by(translatable = True).all():
        percent = json.loads(repository_app.translation_percent)
        for lang_code in lang_codes:
            lang_name = LANGUAGE_NAMES_PER_CODE[lang_code.split('_')[0]]
            cur_percent = percent.get(lang_code, 0.0)
            data_per_language[lang_name].append({
                'name': repository_app.name,
                'url': repository_app.url,
                'thumb': repository_app.app_thumb,
                'percent': 100 * cur_percent,
                'link': 'http://composer.golabz.eu/translator/web/index.html#/edit/{}/ALL/{}'.format(lang_code.rsplit('_', 1)[0], repository_app.url),
            })

    apps_translated = {
        # language: number of apps 100% translated
    }

    for lang, lang_data in data_per_language.items():
        lang_data.sort(lambda x, y: cmp(x['percent'], y['percent']), reverse=True)
        apps_translated[lang] = len([ app for app in lang_data if app['percent'] >= 100 ])

    return render_template("translator/status.html", translations_per_languages = translations_per_languages, total = total, data_per_language = data_per_language, apps_translated=apps_translated, total_apps = total_apps)

@translator_stats_blueprint.route('/golabz')
@public
def stats_golabz():
    try:
        labs = requests.get('https://www.golabz.eu/rest/labs/retrieve.json', timeout = (30, 30)).json()
    except:
        return "Error accessing www.golabz.eu"

    total_labs = len(labs)

    sg_labs = []
    ac_labs = []
    other_labs = []
    total_lab_apps = 0

    for lab in labs:
        for lab_app in lab['lab_apps']:
            total_lab_apps += 1
            app_url = lab_app['app_url']
            if app_url.startswith('http://gateway.golabz.eu/embed/'):
                ac_labs.append(lab)
                break
            elif app_url.startswith('http://gateway.golabz.eu/'):
                sg_labs.append(lab)
                break
            elif 'weblab.deusto.es/golab/labmanager' in app_url:
                sg_labs.append(lab)
                break
            else:
                other_labs.append(lab)

    return render_template("translator/stats_golabz.html", total_labs = total_labs, total_lab_apps=total_lab_apps, sg_labs = sg_labs, ac_labs = ac_labs, other_labs=other_labs, len_sg_labs = len(sg_labs), len_ac_labs = len(ac_labs), len_other_labs=len(other_labs))


@translator_stats_blueprint.route('/missing')
@public
def stats_missing():
    threshold = request.args.get('threshold', 100 * LANGUAGE_THRESHOLD)
    try:
        threshold = float(threshold)
    except (ValueError, TypeError):
        threshold = 100 * LANGUAGE_THRESHOLD
    threshold = threshold / 100.0

    non_automatic_translation_urls = db.session.query(TranslationUrl, TranslatedApp, RepositoryApp).filter(TranslationUrl.automatic == False, TranslationUrl.id == TranslatedApp.translation_url_id, TranslatedApp.url == RepositoryApp.url, RepositoryApp.translation_percent != None, RepositoryApp.translation_percent != "").all()

    missing_translations = []
    for translation_url, translated_app, repository_app in non_automatic_translation_urls:
        original_translations = (repository_app.original_translations or '').split(',')
        if len(original_translations) == 1 and original_translations[0] == '':
            original_translations = []
        original_translations = set([ lang.split('_')[0] for lang in original_translations ])

        translation_percent = json.loads(repository_app.translation_percent or "{}")
        additions = {}
        modifications = {}
        for lang, value in translation_percent.items():
            if value >= threshold:
                if lang.split('_')[0] not in original_translations:
                    additions[tuple(lang.rsplit('_', 1))] = value
                else:
                    pass
                    # TODO: if it is in the original_translations, compare. If there was any change, it must also be reported.
                    # We can't use from_default or from_developer; we need a new variable

        current_record = {
                'repo_app' : repository_app,
                'additions' : additions,
                'modifications' : modifications,
                'contact' : [ subscription.recipient.email for subscription in translation_url.subscriptions ],
            }
        if modifications or additions:
            missing_translations.append(current_record)

    return render_template("translator/stats_missing.html", missing_translations=missing_translations)


@translator_stats_blueprint.route('/users')
@requires_golab_login
def translation_users():
    users = db.session.query(GoLabOAuthUser.display_name, GoLabOAuthUser.email, GoLabOAuthUser.id).all()
    users_by_gravatar = []

    texts_by_user = {
        # email: number
    }
    apps_by_user = {
        # email: number
    }
    langs_by_user = {
        # email: lang_list
    }

    for number, email in db.session.query(func.count(ActiveTranslationMessage.id), GoLabOAuthUser.email).filter(ActiveTranslationMessage.history_id == TranslationMessageHistory.id, TranslationMessageHistory.user_id == GoLabOAuthUser.id, ActiveTranslationMessage.taken_from_default == False, ActiveTranslationMessage.from_developer == False, ActiveTranslationMessage.same_tool.in_([True, None])).group_by(GoLabOAuthUser.email).all():
        texts_by_user[email] = number

    for number, email in db.session.query(func.count(func.distinct(TranslationBundle.translation_url_id)), GoLabOAuthUser.email).filter(ActiveTranslationMessage.bundle_id == TranslationBundle.id, ActiveTranslationMessage.history_id == TranslationMessageHistory.id, TranslationMessageHistory.user_id == GoLabOAuthUser.id, ActiveTranslationMessage.taken_from_default == False, ActiveTranslationMessage.from_developer == False, ActiveTranslationMessage.same_tool.in_([True, None])).group_by(GoLabOAuthUser.email).all():
        apps_by_user[email] = number

    for language, email in db.session.query(TranslationBundle.language, GoLabOAuthUser.email).filter(ActiveTranslationMessage.bundle_id == TranslationBundle.id, ActiveTranslationMessage.history_id == TranslationMessageHistory.id, TranslationMessageHistory.user_id == GoLabOAuthUser.id, ActiveTranslationMessage.taken_from_default == False, ActiveTranslationMessage.from_developer == False, ActiveTranslationMessage.same_tool.in_([True, None])).group_by(TranslationBundle.language, GoLabOAuthUser.email).all():
        if email not in langs_by_user:
            langs_by_user[email] = [ language.split('_')[0] ]
        else:
            langs_by_user[email].append(language.split('_')[0])

    for display_name, email, user_id in users:
        gravatar_url = 'http://gravatar.com/avatar/%s?s=40&d=identicon' % hashlib.md5(email).hexdigest()
        languages = langs_by_user.get(email, [])
        users_by_gravatar.append({
            'gravatar_url': gravatar_url,
            # 'display_name': display_name.strip().replace('.', ' ').title().split(' ')[0],
            'display_name': display_name.strip(),
            'email': email,
            'texts':  texts_by_user.get(email, 0),
            'apps': apps_by_user.get(email, 0),
            'langs': '{}: {}'.format(len(languages), ', '.join(languages)),
            'user_id': user_id,
        })

    return render_template('translator/users.html', users_by_gravatar = users_by_gravatar)

@translator_stats_blueprint.route('/suggestions')
def suggestions():
    total_messages = db.session.query(ActiveTranslationMessage).filter(ActiveTranslationMessage.bundle_id == TranslationBundle.id, TranslationBundle.language == u'en_ALL', TranslationBundle.target == u'ALL').count()
    distinct_messages = { (value or u'') for value,  in db.session.query(ActiveTranslationMessage.value).filter(ActiveTranslationMessage.bundle_id == TranslationBundle.id, TranslationBundle.language == u'en_ALL', TranslationBundle.target == u'ALL').all() }

    distinct_short_messages = [ unicode(hashlib.md5(msg.encode('utf8')).hexdigest()) for msg in distinct_messages ]

    english_stats = {
        'total_messages': total_messages,
        'total_distinct': len(distinct_messages),
        'length': sum([ len(msg) for msg in distinct_messages ]),
        'engines': dict(db.session.query(TranslationExternalSuggestion.engine, func.count(TranslationExternalSuggestion.id)).group_by(TranslationExternalSuggestion.engine)),
    }

    data_per_engine = {
        # engine: {
            # lang: number
        # }
    }

    languages = [
        (code, get_locale_english_name(code, 'ALL'))
        for code in ALL_LANGUAGES
        if code != 'en' and '_' not in code
    ]
    for code in ALL_LANGUAGES:
        if '_' in code and code[0] != 'en':
            languages.append((code, get_locale_english_name(code.split('_')[0], code.split('_')[1])))

    languages.sort(lambda (c1, n1), (c2, n2): cmp(n1, n2))
    lang_codes = [ code for (code, name) in languages ]

    supported = {
        # engine: [ code1, code2... ]
        'google': { lang for lang in google_translator.languages if lang in lang_codes },
        'microsoft': { lang for lang in microsoft_translator.languages if lang in lang_codes  },
        'deepl': { lang for lang in deepl_translator.languages if lang in lang_codes },
    }

    engines = ['google', 'microsoft', 'deepl']

    for count, engine, language in db.session.query(func.count(TranslationExternalSuggestion.id), TranslationExternalSuggestion.engine, TranslationExternalSuggestion.language).filter(TranslationExternalSuggestion.human_key_hash.in_(distinct_short_messages), TranslationExternalSuggestion.origin_language == u'en').group_by(TranslationExternalSuggestion.engine, TranslationExternalSuggestion.language).all():
        if engine not in data_per_engine:
            data_per_engine[engine] = {}
        data_per_engine[engine][language] = count

    data_per_language = {
        # language: count
    }
    for count, language in db.session.query(func.count(func.distinct(TranslationExternalSuggestion.human_key_hash)), TranslationExternalSuggestion.language).filter(TranslationExternalSuggestion.human_key_hash.in_(distinct_short_messages), TranslationExternalSuggestion.origin_language == u'en').group_by(TranslationExternalSuggestion.language).all():
        data_per_language[language] = count

    dict_dates_by_engine = {
        # date: {
        #    engine: count
        # }
    }

    for date, engine, count in db.session.query(func.date(TranslationExternalSuggestion.created), TranslationExternalSuggestion.engine, func.count(TranslationExternalSuggestion.id)).filter(TranslationExternalSuggestion.created >= datetime.datetime(2017, 7, 29)).group_by(func.date(TranslationExternalSuggestion.created), TranslationExternalSuggestion.engine).order_by(func.date(TranslationExternalSuggestion.created)).all():
        date_str = date.strftime('%Y-%m-%d')
        if date_str not in dict_dates_by_engine:
            dict_dates_by_engine[date_str] = {}
        dict_dates_by_engine[date_str][engine] = count

    dates_by_engine = [
        [date] + [ dict_dates_by_engine[date].get(engine, 0) for engine in engines]
        for date in sorted(dict_dates_by_engine.keys(), reverse=True)
    ]

    return render_template("translator/stats_suggestions.html", data_per_engine=data_per_engine, supported=supported, english_stats=english_stats, languages=languages, engines=engines, data_per_language=data_per_language, dates_by_engine=dates_by_engine)

@translator_stats_blueprint.route('/status.json')
def apps_status():
    flash = set([])
    ssl = set([])
    failing = set([])

    for app in db.session.query(RepositoryApp).filter(or_(RepositoryApp.failing == True, RepositoryApp.supports_ssl == False, RepositoryApp.contains_flash == True)).all():
        if app.contains_flash == True:
            flash.add(app.app_link)
        if app.supports_ssl == False:
            ssl.add(app.app_link)
        if app.failing == True:
            failing.add(app.app_link)

    return jsonify(flash=list(flash), ssl=list(ssl), failing=list(failing))

def _get_last_general_check_stats():
    check_urls, = db.session.query(func.count(func.distinct(RepositoryAppCheckUrl.url))).filter_by(active=True).first()
    last_check, = db.session.query(func.min(RepositoryAppCheckUrl.last_update)).filter_by(active=True).first()
    delta = datetime.datetime.utcnow() - last_check
    return {
        'last_check': last_check,
        'days': delta.days,
        'hours': delta.seconds // 3600,
        'minutes': (delta.seconds % 3600) // 60,
        'check_urls': check_urls,
        'split': _split,
    }

def _split(failing_apps):
    recent = []
    over_day = []
    over_week = []

    for failing_app in failing_apps:
        hours = (datetime.datetime.utcnow() - failing_app.failing_since).total_seconds() // 3600
        if hours < 24:
            recent.append(failing_app)
        elif hours < 24 * 7:
            over_day.append(failing_app)
        else:
            over_week.append(failing_app)
    return over_week, over_day, recent

@translator_stats_blueprint.route('/failing/')
@public
def apps_failing():
    failing_apps = db.session.query(RepositoryApp).filter_by(failing = True).options(joinedload('check_urls')).all()
    stats = _get_last_general_check_stats()
    return render_template("translator/failing_apps.html", failing_apps = failing_apps, header = "Failing labs and apps", show_since=True, what = 'working', stats=stats)

@translator_stats_blueprint.route('/failing.json')
@public
def apps_failing_json():
    try:
        hours = int(request.args.get('hours', 24))
    except:
        hours = 24

    failing_since = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
    failing_apps = db.session.query(RepositoryApp).filter_by(failing = True, repository='golabz').filter(RepositoryApp.failing_since <= failing_since).options(joinedload('check_urls')).all()

    failing_ids = sorted(set([ failing_app.external_id.split('-')[0] for failing_app in failing_apps ]))

    per_id = {
        # id: {
        #    'url': app_link,
        #    'failing_urls': [ ... ]
        # }
    }
    for failing_app in failing_apps:
        failing_id = failing_app.external_id.split('-')[0]
        app_link = failing_app.app_link
        failing_urls = []
        for check_url in failing_app.check_urls:
            if check_url.active and check_url.working == False:
                failing_urls.append(check_url.url)
        per_id[failing_id] = {
            'url': app_link,
            'failing_urls': failing_urls,
        }

    return jsonify(
        failing_ids=failing_ids,
        explanation=per_id,
    )


@translator_stats_blueprint.route('/ssl/')
@public
def apps_ssl():
    failing_apps = db.session.query(RepositoryApp).filter_by(supports_ssl = False).options(joinedload('check_urls')).all()
    domains = {}
    for app in failing_apps:
        current_domains = set([])
        for check_url in app.check_urls:
            if check_url.supports_ssl == False:
                hostname = urlparse.urlparse(check_url.url).hostname
                current_domains.add(hostname)
        for domain in current_domains:
            if domain not in domains:
                domains[domain] = 0
            domains[domain] += 1
    sorted_domains = sorted(domains.items(), lambda (k1, c1), (k2, c2): cmp(c2, c1))
    stats = _get_last_general_check_stats()
    return render_template("translator/failing_apps.html", failing_apps = failing_apps, header = "Labs and apps without https support", show_since=False, what = 'ssl', sorted_domains=sorted_domains, stats=stats)

@translator_stats_blueprint.route('/flash/')
@public
def apps_flash():
    failing_apps = db.session.query(RepositoryApp).filter_by(contains_flash = True).options(joinedload('check_urls')).all()
    stats = _get_last_general_check_stats()
    return render_template("translator/failing_apps.html", failing_apps = failing_apps, header = "Labs and apps using Flash", show_since=False, what = 'flash', stats=stats)

@translator_stats_blueprint.route('/users/<int:user_id>')
@requires_golab_login
def translation_user(user_id):
    user = db.session.query(GoLabOAuthUser).filter_by(id=user_id).first()
    if not user:
        return "User not found", 404

    translation_dates = db.session.query(func.max(ActiveTranslationMessage.datetime), func.min(ActiveTranslationMessage.datetime)).filter(ActiveTranslationMessage.history_id == TranslationMessageHistory.id, TranslationMessageHistory.user_id == user.id, ActiveTranslationMessage.taken_from_default == False, ActiveTranslationMessage.from_developer == False, ActiveTranslationMessage.same_tool.in_([True, None])).first()
    if translation_dates is None:
        return "User has no translation"

    last_translation, first_translation = translation_dates

    user_translations = db.session.query(func.count(ActiveTranslationMessage.id), TranslationBundle).filter(ActiveTranslationMessage.bundle_id == TranslationBundle.id, ActiveTranslationMessage.history_id == TranslationMessageHistory.id, TranslationMessageHistory.user_id == user_id, ActiveTranslationMessage.taken_from_default == False, ActiveTranslationMessage.from_developer == False, ActiveTranslationMessage.same_tool.in_([True, None])).group_by(TranslationBundle.id).options(joinedload('translation_url')).all()

    translation_bundles_by_id = { tr_bundle.id: tr_bundle for (count, tr_bundle) in user_translations }

    translation_urls = [ bundle.translation_url_id for bundle in translation_bundles_by_id.values() ]
    translation_apps_by_url = { tr_app.translation_url.url : tr_app for tr_app in db.session.query(TranslatedApp).filter(TranslatedApp.translation_url_id.in_(translation_urls)).options(joinedload('translation_url')).all() }
    repository_app_by_url = { repo.url: repo for repo in db.session.query(RepositoryApp).filter(RepositoryApp.url.in_([tr_app.url for tr_app in translation_apps_by_url.values()])).all() }
    
    translation_app_info = {
        # translation_app_url: {
            # translations: {
            #      language: count,
            # }
            # golabz: {
            #     'name': name,
            #     'thumb': thumb
            #     'link': link to golabz
            # }
        # }
    }

    translation_url_info = {
        # translation_url: {
        #    language: count
        # }
    }

    per_lang = {
        # lang: count
    }

    total = 0

    for count, tr_bundle in user_translations:
        tr_url = tr_bundle.translation_url.url
        tr_app = translation_apps_by_url.get(tr_url)
        lang = tr_bundle.language.split('_')[0]
        if lang not in per_lang:
            per_lang[lang] = 0
        per_lang[lang] += count
        total += count

        if tr_app:
            if tr_app.url not in translation_app_info:
                translation_app_info[tr_app.url] = {
                    'url': tr_app.url,
                    'translations': {}
                }

            if lang in translation_app_info[tr_app.url]['translations']:
                # Should never happen, but there were suspcious of corrupted data in the database
                sys.stderr.write("WARNING: REPEATED URL\n")
                sys.stderr.flush()
                
            translation_app_info[tr_app.url]['translations'][lang] = count
            if not 'golabz' in translation_app_info[tr_app.url]:
                repo_app = repository_app_by_url.get(tr_app.url)
                if repo_app:
                    translation_app_info[tr_app.url]['golabz'] = {
                        'name': repo_app.name,
                        'thumb': repo_app.app_thumb,
                        'link': repo_app.app_link or '',
                    }
        else:
            if tr_url not in translation_url_info:
                translation_url_info[tr_url] = {}
    
            if lang in translation_url_info[tr_url]:
                # Should never happen, but there were suspcious of corrupted data in the database
                sys.stderr.write("WARNING: REPEATED URL\n")
                sys.stderr.flush()

            translation_url_info[tr_url][lang] = count

    # Sorting
    per_lang_sorted = sorted([ { 'lang': lang, 'count' : count } for (lang, count) in per_lang.items() ], lambda x, y: cmp(y['count'], x['count']))

    golabz_apps = sorted(
        [
            tr_app_info
            for tr_app_info in translation_app_info.values()
            if 'golabz' in tr_app_info
        ], 
            lambda x, y: cmp(
                reduce(operator.add, y['translations'].values()), 
                reduce(operator.add, x['translations'].values())
             ))

    non_golabz_apps = sorted(
        [
            tr_app_info
            for tr_app_info in translation_app_info.values()
            if 'golabz' not in tr_app_info
        ], 
            lambda x, y: cmp(
                reduce(operator.add, y['translations'].values()), 
                reduce(operator.add, x['translations'].values())
             ))

    gravatar_url = 'http://gravatar.com/avatar/%s?s=150&d=identicon' % hashlib.md5(user.email).hexdigest()

    lang_link = lambda lang, app_url: url_for('translator_dev.translations_revisions', lang=lang + '_ALL', target='ALL', app_url=app_url)

    return render_template("translator/user.html", last_translation = last_translation, first_translation = first_translation, gravatar_url=gravatar_url, per_lang = per_lang_sorted, user=user, total=total, golabz_apps=golabz_apps, non_golabz_apps=non_golabz_apps, non_apps=translation_url_info, lang_link=lang_link)

