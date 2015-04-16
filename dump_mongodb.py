import urllib2
import pprint
import json
import os

from bson import json_util
from pymongo import MongoClient

from appcomposer import app

if not os.path.exists("dump"):
    os.mkdir("dump")

def convert(message):
    try:
        return data.encode('latin1').decode('utf8')
    except UnicodeDecodeError:
        return message
    except UnicodeEncodeError:
        return message

mongodb_uri = app.config['MONGODB_PUSHES_URI']
mongo_client = MongoClient(mongodb_uri)
mongo_bundles = mongo_client.appcomposerdb.bundles

for translation in mongo_bundles.find():
    translation_id = urllib2.quote(translation['_id'], '').replace('%','_')
    data = translation['data']
    messages = json.loads(data)
    new_messages = {}
    for key, value in messages.iteritems():
        new_messages[convert(key)] = convert(value)
    translation['data'] = json.dumps(data)
    open('dump/%s.json' % translation_id, 'w').write(json.dumps(translation, indent = 4, default=json_util.default))
