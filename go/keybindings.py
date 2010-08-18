# Python global key bindings by Luca Bruno 2008 <lethalman88@gmail.com>
# Modifications by Donald Harvey <donald@donaldharvey.co.uk>
#
# This a slightly modified version of the globalkeybinding.py file which is part of FreeSpeak.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import gobject
import gtk
import Xlib
from Xlib.display import Display
from Xlib import X
import threading
from functools import partial


class InvalidBindingException(ValueError):
    pass

class KeyBindingManager(threading.Thread):
    """
    An Xlib-based global key bindings manager.
    """
    def __init__(self):
        super(KeyBindingManager, self).__init__()
        self.daemon = True
        self.display = Display()
        self.root = self.display.screen().root
        self._binding_map = {}

        self.known_modifiers_mask = 0
        gdk_modifiers = (gtk.gdk.CONTROL_MASK, gtk.gdk.SHIFT_MASK, gtk.gdk.MOD1_MASK,
            gtk.gdk.MOD2_MASK, gtk.gdk.MOD3_MASK, gtk.gdk.MOD4_MASK, gtk.gdk.MOD5_MASK,
            gtk.gdk.SUPER_MASK, gtk.gdk.HYPER_MASK)
        for mod in gdk_modifiers:
            self.known_modifiers_mask |= mod


    def add_binding(self, binding_string, action, *args, **kwargs):
        """
        Add a key binding from an accelerator string.
        Uses gtk.accelerator_parse to parse the string; according to the docs,
        this is "fairly liberal" and "allows abbreviations such as '<Ctrl>' and '<Ctl>'".
        """
        print 'Adding', binding_string
        keyval, modifiers = gtk.accelerator_parse(binding_string)
        print modifiers
        print keyval
        if keyval == 0:
            raise InvalidBindingException('The binding %s is invalid.' % repr(binding_string))
        action = partial(action, *args, **kwargs)
        keycode = gtk.gdk.keymap_get_default().get_entries_for_keyval(keyval)[0][0]
        self._binding_map[(keycode, modifiers)] = action
        self.regrab()

    def grab(self):
        for (keycode, modifiers) in self._binding_map.keys():
            self.root.grab_key(keycode, int(modifiers), True, X.GrabModeAsync, X.GrabModeSync)

    def ungrab(self):
        for (keycode, modifiers) in self._binding_map.keys():
            self.root.ungrab_key(keycode, modifiers, self.root)

    def regrab(self):
        self.ungrab()
        self.grab()


    def _action_idle(self, action):
        gtk.gdk.threads_enter()
        gobject.idle_add(action)
        gtk.gdk.threads_leave()
        return False

    def run(self):
        self.running = True
        wait_for_release = False
        while self.running:
            event = self.display.next_event()
            if event.type == X.KeyPress and not wait_for_release:
                keycode = event.detail
                modifiers = event.state & self.known_modifiers_mask
                try:
                    action = self._binding_map[(keycode, modifiers)]
                except KeyError:
                    # This key binding isn't mapped.
                    self.display.allow_events(X.ReplayKeyboard, event.time)
                else:
                    # Get the action ready for when the key combo is released
                    wait_for_release = True
                    self.display.allow_events(X.AsyncKeyboard, event.time)
                    self._upcoming_action = (keycode, modifiers, action)

            elif event.type == X.KeyRelease and wait_for_release and event.detail == self._upcoming_action[0]:
                # The user has released the key combo; run the queued action
                wait_for_release = False
                action = self._upcoming_action[2]
                del self._upcoming_action
                gobject.idle_add(self._action_idle, action)
                self.display.allow_events(X.AsyncKeyboard, event.time)

            else:
                self.display.allow_events(X.ReplayKeyboard, event.time)

    def stop(self):
        self.running = False
        self.ungrab()
        self.display.close()