SHINDIG_SERVER = 'http://shindig.epfl.ch'


def shindig_url(relative_url):
    return '%s%s' % (SHINDIG_SERVER, relative_url)