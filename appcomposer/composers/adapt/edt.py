data = {
    'new' : 'edt_new', # pointer to function
    'load' : 'edt_load', # pointer to function
    'id' : 'edt', # so when loading an application, we know which handle to use, EQUIVALE AL TIPO QUE HABIA DEFINIDO
}


def edt_new():
    # ...
    x = 5
    return x    

def edt_load():
    # ...
    return "load"    
