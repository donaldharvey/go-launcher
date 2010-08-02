from go.commands import Command
import re
import math
from functools import partial
import parser
from StringIO import StringIO
import tokenize
import token
from decimal import Decimal

class SimpleCalcCommand(Command):
    name = 'calc'
    nice_name = 'Calculate'
    caption = 'Calculate simple operations.'
    def _copy_to_clipboard(self, value):
        clipboard = gtk.clipboard_get('CLIPBOARD')
        clipboard.set_text(value)

    def _eval(self, value):
        result = []
        g = tokenize.generate_tokens(StringIO(value).readline)   # tokenize the string
        for toknum, tokval, _, _, _  in g:
            if toknum == token.NUMBER:  # replace NUMBER tokens
                result.extend([
                    (token.NAME, 'Decimal'),
                    (token.OP, '('),
                    (token.STRING, repr(tokval)),
                    (token.OP, ')')
                ])
            else:
                result.append((toknum, tokval))
        context = {
            'Decimal': Decimal
        }
        context.update(math.__dict__)
        return eval(tokenize.untokenize(result), context, {})

    def lookup(self, value):
        try:
            result = self._eval(value)
            return [{
                'title': str(result),
                'caption': 'Copy this result to the clipboard.',
                'callback': partial(self._copy_to_clipboard, value),
            }]
        except Exception:
            import traceback; traceback.print_exc()
            return []

    def execute(self, value):
        result = self._eval(value)
        self._copy_to_clipboard(str(result))

commands = [
    SimpleCalcCommand
]
