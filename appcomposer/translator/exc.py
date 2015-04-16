from appcomposer.exceptions import AppComposerError

class TranslatorError(AppComposerError):
    def __init__(self, message, code = 500, *args):
        self.code = code
        super(TranslatorError, self).__init__(message, code, *args)
