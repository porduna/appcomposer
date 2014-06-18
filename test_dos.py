import requests

target = """http://www.weblab.deusto.es/golab/appcomposer.dev/"""

bot = requests.session()

r = bot.post(target + "login-local", data={"login": "admin", "password": "password"})

r = bot.post(target + "composers/translate/selectlang", data={"appurl": "http://dl.dropboxusercontent.com/u/6424137/i18n.xml", "appname": "ATTACK"})

print r.text