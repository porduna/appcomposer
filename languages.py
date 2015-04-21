official_languages = """Bulgarian bg
Croatian hr
Czech cs
Danish da
Dutch nl
English en
Estonian et
Finnish fi
French fr
German de
Greek el
Hungarian hu
Irish ga
Italian it
Latvian lv
Lithuanian lt
Maltese mt
Polish pl
Portuguese pt
Romanian ro
Slovak sk
Slovene sl
Spanish es
Swedish sv"""

semiofficial_languages = """Basque eu
Catalan ca
Galician gl
Scottish gd
Welsh cy"""

official_language_codes = [ line.split() for line in official_languages.splitlines() ]
semiofficial_language_codes = [ line.split() for line in semiofficial_languages.splitlines() ]

all_languages = official_language_codes[:]
all_languages.extend(semiofficial_language_codes)

print "Official"
print [ code for (lang, code) in official_language_codes ]
print "Semiofficial"
print [ code for (lang, code) in semiofficial_language_codes ]

