import gtk
import cairo
import pango
import pangocairo
import os
import time
from go.utils.tweener import Tweener, Easing
tweener = Tweener()
from glib import markup_escape_text
import datetime as dt
from functools import partial
from go.commands import find_commands
from threading import Thread
import gobject
import signal

from go.ui.mainwindow import GoWindow

#RESOURCES_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'resources'))

if __name__ == '__main__':
    g = GoWindow()
    g.main()
