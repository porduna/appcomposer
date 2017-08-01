import datetime
import traceback
import smtplib
from collections import defaultdict
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from flask import render_template, current_app
from appcomposer import redis_store
from appcomposer.db import db
from appcomposer.models import TranslationSubscription, TranslationNotificationRecipient, TranslationUrl, TranslationBundle, ActiveTranslationMessage, GoLabOAuthUser, TranslationMessageHistory, TranslatedApp, RepositoryApp

def run_notifications():
    print "Starting notifications process"
    # MIN_INTERVAL = 30 # minutes
    STILL_WORKING = 5 # minutes 
    # last_period = datetime.datetime.utcnow() - datetime.timedelta(minutes = MIN_INTERVAL)
    still_working_period = datetime.datetime.utcnow() - datetime.timedelta(minutes = STILL_WORKING)

    default_email = current_app.config.get('TRANSLATOR_DEFAULT_EMAIL', 'weblab+appcomposer@deusto.es')
    default_user = db.session.query(GoLabOAuthUser).filter_by(email = default_email).first()
    if default_user:
        default_user_id = default_user.id
    else:
        default_user_id = -1
    
    # Get subscriptions that have not been checked in this period
    subscriptions = db.session.query(TranslationSubscription.id, TranslationSubscription.translation_url_id, TranslationSubscription.last_check, TranslationSubscription.recipient_id).all()
    if not subscriptions:
        print "Finish: no subscription"
        return
    
    # When was the oldest last notification?
    # min_last_check = min([ sub.last_check for sub in subscriptions ])

    # Now, get the list of translation_url_ids
    translation_url_ids = [ translation_url_id for subscription_id, translation_url_id, last_check, recipient_id in subscriptions ]

    if not translation_url_ids:
        print "Finish: no translation_url_id means no active message"
        return

    # And retrieve all the active messages which have been updated at least some minutes ago (otherwise it seems that somebody is still working),
    active_messages = (db.session.query(func.max(ActiveTranslationMessage.datetime), TranslationBundle.id, TranslationBundle.translation_url_id)
                        .filter(
                            TranslationBundle.translation_url_id.in_(translation_url_ids), 
                            ActiveTranslationMessage.bundle_id == TranslationBundle.id, 
                            ActiveTranslationMessage.history_id == TranslationMessageHistory.id, 
                            ActiveTranslationMessage.taken_from_default == False, 
                            ActiveTranslationMessage.from_developer == False, 
                            TranslationMessageHistory.user_id != default_user_id)
                        .group_by(TranslationBundle.id)
                        .having(func.max(ActiveTranslationMessage.datetime) < still_working_period).all())
    
    if not active_messages:
        print "Finish: no active message"
        return
    
    # Calculate the maximum last update
    active_messages_by_url_id = {
        # translation_url_id: last_message_update (when was the last message update)
    }
    for active_message_last_update, bundle_id, translation_url_id in active_messages:
        if translation_url_id not in active_messages_by_url_id:
            active_messages_by_url_id[translation_url_id] = active_message_last_update
        else:
            if active_messages_by_url_id[translation_url_id] < active_message_last_update:
                active_messages_by_url_id[translation_url_id] = active_message_last_update

    pending_emails = {
        # recipient_id : {
        #    translation_url_id : {
        #        language : {
        #            user_id : 5 # number of changes
        #        }
        #    }
        # }
    }
    all_user_ids = set()
    all_recipient_ids = set()
    all_translation_url_ids = set()

    any_update = False

    for subscription_id, translation_url_id, last_check, recipient_id in subscriptions:
        last_update = active_messages_by_url_id.get(translation_url_id, datetime.datetime(1980,1,1))
        # Check if the last check was before the last update. If so, there is something to notify
        if last_check < last_update:
            changes = {
                # language : {
                #    user_id : number
                # }
            }
            changes_per_language = (db.session.query(TranslationMessageHistory.user_id, func.count(ActiveTranslationMessage.id), TranslationBundle.language)
                                    .filter(
                                        ActiveTranslationMessage.bundle_id == TranslationBundle.id, 
                                        TranslationBundle.translation_url_id == translation_url_id, 
                                        ActiveTranslationMessage.datetime > last_check, 
                                        TranslationMessageHistory.user_id != default_user_id, 
                                        ActiveTranslationMessage.taken_from_default == False, 
                                        ActiveTranslationMessage.from_developer == False, 
                                        ActiveTranslationMessage.history_id == TranslationMessageHistory.id
                                    ).group_by(TranslationBundle.language, TranslationMessageHistory.user_id).all())
            for user_id, number_of_changes, language in changes_per_language:
                if number_of_changes:
                    if language not in changes:
                        changes[language] = {}
                    changes[language][user_id] = number_of_changes
                    all_user_ids.add(user_id)
                    all_recipient_ids.add(recipient_id)
                    all_translation_url_ids.add(translation_url_id)

            if changes:
                if recipient_id not in pending_emails:
                    pending_emails[recipient_id] = {}

                pending_emails[recipient_id][translation_url_id] = changes

                subscription = db.session.query(TranslationSubscription).filter_by(id = subscription_id).first()
                if subscription:
                    subscription.update()
                    any_update = True


    if not all_user_ids:
        # Nothing to notify
        print "No user to notify"
        return

    if any_update:
        try:
            db.session.commit()
        except:
            traceback.print_exc()
            db.session.rollback()
            send_notification([], "Error commiting notification changes to the database: {}".format(traceback.format_exc()), None, "Error in notifications in appcomposer")
            # If the update fails, we can have the risk that the message is sent twice. Better fail
            raise

    # Lookup all the users and recipients involved
    users_by_id = {}
    for user in db.session.query(GoLabOAuthUser).filter(GoLabOAuthUser.id.in_(list(all_user_ids))).all():
        users_by_id[user.id] = user

    recipients_by_id = {}
    if all_recipient_ids:
        for recipient in db.session.query(TranslationNotificationRecipient).filter(TranslationNotificationRecipient.id.in_(list(all_recipient_ids))).all():
            recipients_by_id[recipient.id] = recipient

    translation_urls_by_id = {}
    if all_translation_url_ids:
        for translation_url in db.session.query(TranslationUrl).filter(TranslationUrl.id.in_(list(all_translation_url_ids))).all():
            translation_urls_by_id[translation_url.id] = translation_url
    
    translation_apps_by_translation_url_id = defaultdict(list)
    if all_translation_url_ids:
        for translation_app in db.session.query(TranslatedApp).filter(TranslatedApp.translation_url_id.in_(list(all_translation_url_ids))).all():
            translation_apps_by_translation_url_id[translation_app.translation_url_id].append(translation_app.url)

    all_translation_urls = []
    for translation_apps in translation_apps_by_translation_url_id.values():
        all_translation_urls.extend([ translation_app for translation_app in translation_apps ])

    repository_names_by_translation_app = {
        # url: name
    }
    if all_translation_urls:
        for repository_app in db.session.query(RepositoryApp).filter(TranslatedApp.url.in_(all_translation_urls)).all():
            repository_names_by_translation_app[repository_app.url] = repository_app.name
    

    for recipient_id, recipient_messages in pending_emails.iteritems():
        translation_urls = []
        txt_msg = "Hi,\nThe following changes have been detected in applications on which you're subscribed:\n"
        html_translations = []

        names_for_subject = set()
        for translation_url_id, translation_url_changes in recipient_messages.iteritems():
            translation_url = translation_urls_by_id[translation_url_id].url
            translation_urls.append(translation_url)
            txt_msg += " - %s \n" % translation_url
            translation_apps = translation_apps_by_translation_url_id[translation_url_id]

            current_name_for_subject = None
            fallback_name_for_subject = set()
            if translation_apps:
                for translation_app in translation_apps:
                    # Title if name not found
                    if current_name_for_subject is None and translation_app in repository_names_by_translation_app:
                        current_name_for_subject = repository_names_by_translation_app[translation_app]
                    else:
                        fallback_name_for_subject.add(translation_app)

            # Names
            if current_name_for_subject is None:
                if fallback_name_for_subject:
                    current_name_for_subject = '; '.join(fallback_name_for_subject)
                else:
                    current_name_for_subject = translation_url
            names_for_subject.add(current_name_for_subject)

            html_changes = []
            for language, language_changes in translation_url_changes.iteritems():
                txt_msg += "   * %s\n" % language
                for user_id, number_of_changes in language_changes.iteritems():
                    user = users_by_id[user_id]
                    txt_msg += "     + %s <%s> has made %s changes on the %s translation\n" % (user.display_name, user.email, number_of_changes, language)
                    html_changes.append((language, {
                        'mail': user.email,
                        'name': user.display_name,
                    }, number_of_changes))
            txt_msg += "\n"
            
            cur_record = {
                'name': current_name_for_subject,
                'changes': html_changes,
            }
            if translation_apps:
                cur_record['url'] = translation_apps[0]
            else:
                cur_record['url'] = None

            html_translations.append(cur_record)

        txt_msg += "\nYou can find the translations in different formats in:\n    - http://composer.golabz.eu/translator/dev/apps/\n\n"
        txt_msg += "\nIf you don't want to receive these messages, please reply this e-mail.\n\n--\nThe Go-Lab App Composer team"

        recipient = recipients_by_id[recipient_id]
        html_msg = render_template("emails/changes.html", translations=html_translations)
        
        subject = "Translations for %s" % ('; '.join([ name for name in names_for_subject if name ]))
        try:
            send_notification([ recipient.email ], txt_msg, html_msg, subject)
        except:
            traceback.print_exc()
        else:
            print "Notification sent to %s about changes in %s" % (recipient.email, repr(translation_urls))
    print "Finished notification process"

def run_update_notifications():
    app_urls = []
    while True:
        app_url = redis_store.lpop('appcomposer:downloader:changes')
        if app_url:
            app_urls.append(app_url)
        else:
            break

    app_urls = list(set(app_urls)) # Duplicated don't cause two messages or listed twice

    if not app_urls:
        return

    repo_by_app_url = { repo.url: repo for repo in db.session.query(RepositoryApp).filter(RepositoryApp.url.in_(app_urls)).all() }
    translation_apps = { trapp.url: trapp.translation_url.url for trapp in db.session.query(TranslatedApp).filter(TranslatedApp.url.in_(app_urls)).all() }
    repos_by_trurl = {
        # trurl: [ trapp ]
    }
    for trapp, trurl in translation_apps.items():
        if trurl not in repos_by_trurl:
            repos_by_trurl[trurl] = []

        if trapp in repo_by_app_url:
            repos_by_trurl[trurl].append(repo_by_app_url[trapp])

    translation_urls = db.session.query(TranslationUrl).filter(TranslatedApp.url.in_(app_urls), TranslatedApp.translation_url_id == TranslationUrl.id).all()
    subscriptions = db.session.query(TranslationSubscription).filter(TranslationSubscription.translation_url_id.in_([ trurl.id for trurl in translation_urls ])).options(joinedload('recipient')).all()

    emails = {
        # email: [
        #    {
        #        'name': 'Hypothesis scratchpad',
        #        'app_url': '',
        #    },
        #    {
        #        'name': 'Foo',
        #        'url': '',
        #    }
        # ]
    }
    
    for subscription in subscriptions:
        email = subscription.recipient.email
        
        if email not in emails:
            emails[email] = []

        repos = repos_by_trurl.get(subscription.translation_url.url, [])
        if repos:
            repo = repos[0]
            emails[email].append({
                'name': repo.name,
                'url': repo.url,
            })

    for email, apps in emails.items():
        send_update_notification(email, apps)
        

def send_update_notification(email, apps):
    txt_msg = u"Hi,\n\nThis is a quick mail to confirm that the AppComposer is aware of changes in the following apps:\n"
    for app in apps:
        txt_msg += u" - {} ( {} )\n".format(app['name'], app['url'])
    txt_msg += u"\nThe AppComposer team"
    try:
        send_notification([ email ], txt_msg, None, "Change confirmed")
    except:
        traceback.print_exc()
    

def send_notification(recipients, txt_body, html_body, subject):
    if current_app.config.get('NOTIFICATIONS_DISABLED'):
        return

    if current_app.config.get('NOTIFICATIONS_ONLY_ADMIN'):
        to_addrs = list(current_app.config.get('ADMINS', []))
    else:
        to_addrs = list(current_app.config.get('ADMINS', [])) + list(recipients)

    from_addr = 'weblab@deusto.es'
    
    smtp_server = current_app.config.get("SMTP_SERVER")
    if not smtp_server or not from_addr or not to_addrs:
        print("Skipping mail (no SMTP_SERVER configured)")
        print(txt_body)
        print(html_body)
        return


    msg = MIMEMultipart('alternative')
    msg['Subject'] = "[AppComp] %s" % subject
    msg['From'] = "App Composer Translator <weblab@deusto.es>"
    msg['To'] = ', '.join(recipients)

    part1 = MIMEText(txt_body.encode('utf8'), 'plain', _charset='UTF-8')
    msg.attach(part1)
    if html_body:
        part2 = MIMEText(html_body.encode('utf8'), 'html', _charset='UTF-8')
        msg.attach(part2)

    server = smtplib.SMTP(smtp_server)
    server.sendmail(from_addr, to_addrs, msg.as_string())

if __name__ == '__main__':
    from appcomposer.application import app
    with app.app_context():
        run_notifications()

