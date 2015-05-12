import datetime
import traceback
import smtplib
from collections import defaultdict
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy import func

from appcomposer.db import db
from appcomposer.application import app
from appcomposer.models import TranslationSubscription, TranslationNotificationRecipient, TranslationUrl, TranslationBundle, ActiveTranslationMessage, GoLabOAuthUser, TranslationMessageHistory, TranslatedApp

def run_notifications():
    print "Starting notifications process"
    MIN_INTERVAL = 30 # minutes
    STILL_WORKING = 5 # minutes 
    last_period = datetime.datetime.utcnow() - datetime.timedelta(minutes = MIN_INTERVAL)
    still_working_period = datetime.datetime.utcnow() - datetime.timedelta(minutes = STILL_WORKING)

    default_email = app.config.get('TRANSLATOR_DEFAULT_EMAIL', 'weblab+appcomposer@deusto.es')
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
    min_last_check = min([ sub.last_check for sub in subscriptions ])

    # Now, get the list of translation_url_ids
    translation_url_ids = [ translation_url_id for subscription_id, translation_url_id, last_check, recipient_id in subscriptions ]

    # And retrieve all the active messages which have been updated at least some minutes ago (otherwise it seems that somebody is still working),
    active_messages = (db.session.query(func.max(ActiveTranslationMessage.datetime), TranslationBundle.id, TranslationBundle.translation_url_id)
                        .filter(
                            TranslationBundle.translation_url_id.in_(translation_url_ids), 
                            ActiveTranslationMessage.bundle_id == TranslationBundle.id, 
                            ActiveTranslationMessage.history_id == TranslationMessageHistory.id, 
                            TranslationMessageHistory.user_id != default_user_id)
                        .group_by(TranslationBundle.id)
                        .having(func.max(ActiveTranslationMessage.datetime) < still_working_period).all())
    
    if not active_messages:
        print "Finish: no active message"
        return
    
    # Calculate the maximum last update
    active_messages_by_url_id = {}
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
            changes_per_language = db.session.query(TranslationMessageHistory.user_id, func.count(ActiveTranslationMessage.id), TranslationBundle.language).filter(ActiveTranslationMessage.bundle_id == TranslationBundle.id, TranslationBundle.translation_url_id == translation_url_id, ActiveTranslationMessage.datetime > last_check, TranslationMessageHistory.user_id != default_user_id, ActiveTranslationMessage.history_id == TranslationMessageHistory.id).group_by(TranslationBundle.language, TranslationMessageHistory.user_id).all()
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
            db.session.rollback()

    # Lookup all the users and recipients involved
    users_by_id = {}
    for user in db.session.query(GoLabOAuthUser).filter(GoLabOAuthUser.id.in_(list(all_user_ids))).all():
        users_by_id[user.id] = user

    recipients_by_id = {}
    for recipient in db.session.query(TranslationNotificationRecipient).filter(TranslationNotificationRecipient.id.in_(list(all_recipient_ids))).all():
        recipients_by_id[recipient.id] = recipient

    translation_urls_by_id = {}
    for translation_url in db.session.query(TranslationUrl).filter(TranslationUrl.id.in_(list(all_translation_url_ids))).all():
        translation_urls_by_id[translation_url.id] = translation_url
    
    translation_apps_by_translation_url_id = defaultdict(list)
    for translation_app in db.session.query(TranslatedApp).filter(TranslatedApp.translation_url_id.in_(list(all_translation_url_ids))).all():
        translation_apps_by_translation_url_id[translation_app.translation_url_id].append(translation_app.url)

    for recipient_id, recipient_messages in pending_emails.iteritems():
        translation_urls = []
        txt_msg = "Hi,\nThe following changes have been detected in applications on which you're subscribed:\n"
        html_msg = "<p>Hi,</p><p>The following changes have been detected in applications on which you're subscribed:</p><ul>\n"
        for translation_url_id, translation_url_changes in recipient_messages.iteritems():
            translation_url = translation_urls_by_id[translation_url_id].url
            translation_urls.append(translation_url)
            txt_msg += " - %s \n" % translation_url
            html_msg += "<li>%s<ul>" % translation_url
            translation_apps = translation_apps_by_translation_url_id[translation_url_id]
            if translation_apps:
                html_msg += "<li>Applications:<ul>\n"
                for translation_app in translation_apps:
                    html_msg += "<li>%s</li>" % translation_app
                html_msg += "</ul></li>"
            html_msg += "<li>Changes:<ul>\n"
            for language, language_changes in translation_url_changes.iteritems():
                txt_msg += "   * %s\n" % language
                html_msg += "<li>%s<ul>" % language
                for user_id, number_of_changes in language_changes.iteritems():
                    user = users_by_id[user_id]
                    txt_msg += "     + %s <%s> has made %s changes on the %s translation\n" % (user.display_name, user.email, number_of_changes, language)
                    html_msg += "<li>%s <%s> has made %s changes on the %s translation</li>" % (user.display_name, user.email, number_of_changes, language)
                html_msg += "</ul></li>"
            txt_msg += "\n"
            html_msg += "</ul></li></ul>"
            html_msg += "</li>\n"
        txt_msg += "\nYou can find the translations in different formats in:\n    - http://composer.golabz.eu/translator/dev/apps/\n\n"
        html_msg += "</ul><p>You can find the translations <a href='http://composer.golabz.eu/translator/dev/apps/'>here</a>.</p>"
        txt_msg += "\nIf you don't want to receive these messages, please reply this e-mail.\n\n--\nThe Go-Lab App Composer team"
        html_msg += "<p>If you don't want to receive these e-mails, please reply this e-mail.</p><p>--<br>The Go-Lab App Composer team<p>"

        recipient = recipients_by_id[recipient_id]

        try:
            send_notification(recipient.email, txt_msg, html_msg)
        except:
            traceback.print_exc()
        else:
            print "Notification sent to %s about changes in %s" % (recipient.email, repr(translation_urls))
    print "Finished notification process"


def send_notification(recipient, txt_body, html_body):
    ACTIVE = True
    if ACTIVE:
        to_addrs = list(app.config.get('ADMINS', [])) + [ recipient ]
    else:
        to_addrs = list(app.config.get('ADMINS', [])) # + [ recipient ]
    from_addr = 'weblab@deusto.es'

    MAIL_TPL = """From: App Composer Translator <%(sender)s>
    To: %(recipients)s
    Subject: %(subject)s

    %(body)s
    """
    smtp_server = app.config.get("SMTP_SERVER")
    if not smtp_server or not from_addr or not to_addrs:
        return

    msg = MIMEMultipart('alternative')
    msg['Subject'] = "[AppComposer] New translations on your applications"
    msg['From'] = "App Composer Translator <weblab@deusto.es>"
    msg['To'] = recipient

    part1 = MIMEText(txt_body.encode('utf8'), 'plain')
    part2 = MIMEText(html_body.encode('utf8'), 'html')
    msg.attach(part1)
    msg.attach(part2)

    server = smtplib.SMTP(smtp_server)
    server.sendmail(from_addr, to_addrs, msg.as_string())


if __name__ == '__main__':
    with app.app_context():
        run_notifications()

