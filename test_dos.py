import requests

target = """http://www.weblab.deusto.es/golab/appcomposer.dev/"""
#target = "http://localhost:5000/"

bot = requests.session()

r = bot.get(target + "login-local")
r = bot.post(target + "login", data={"login": "testuser", "password": "passwords", "submit": ""})
# print r.text
print r.history
print r.status_code


r = bot.get(target + "composers/translate/selectlang", data={"appurl": "http://dl.dropboxusercontent.com/u/6424137/i18n.xml", "appname": "ATTACK"})

# print r.text