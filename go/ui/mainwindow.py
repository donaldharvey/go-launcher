from go.ui.resultswindow import GoResultsWindow
from go.commands import find_commands
from go.keybindings import KeyBindingManager
from go.utils import rounded_rectangle

import gtk
import cairo
import pango
import pangocairo
import os
import time
import gobject
from glib import markup_escape_text
key_binding_mgr = KeyBindingManager()
import signal

def _char_offset_to_byte_offset(offset, string):
    """Converts a logical character offset to a byte offset."""
    return len(str(unicode(string)[:offset]))

class GoWindow(gtk.Window):
    def __init__(self):
        self._results = []
        gtk.Window.__init__(self)
        self.set_app_paintable(True)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_decorated(False)
        self.set_double_buffered(True)
        self.set_position(gtk.WIN_POS_CENTER_ALWAYS)
        self.set_default_size(120, 120)

        self._searchbox = gtk.Entry()
        #self._fixed = gtk.Fixed()
        #self._results_drawingarea = gtk.DrawingArea()
        #self._results_drawingarea.set_size_request(420, 420)
        #self._fixed.put(self._results_drawingarea, 0, 0)
        #self.add(self._fixed)
        self.add(self._searchbox)
        self._searchbox.hide()
        self.props.opacity = 1

        self.commands = find_commands()

        self.connect('expose-event', self.draw_window)
        #self.connect('realize', self.realize_window)

        def cb(w, e):
            text = self._searchbox.get_text()
            if e.keyval == 65307: # Escape
                self.hide()
                gtk.gdk.keyboard_ungrab()
            elif e.keyval == 65293: # Return
                if self.results_window.results:
                    try:
                        command_arg = text.split(' ', 1)[1]
                    except IndexError:
                        command_arg = ''
                    self.results_window.results[self.results_window.cursor_position].run(command_arg)
                    self.hide()
                    gtk.gdk.keyboard_ungrab()

            elif e.keyval == 65362: # Up arrow
                self.results_window.move_cursor('up')
            elif e.keyval == 65364: # Down arrow
                self.results_window.move_cursor('down')


            self._searchbox.emit('key-press-event', e)
            self.queue_draw()
        self.connect('key-press-event', cb)
        self.connect('key-release-event', lambda w, e: self._searchbox.do_key_release_event(self._searchbox, e))
        self._searchbox.connect('changed', self.searchbox_changed)

        self.do_screen_changed(self)
        self.results_window = GoResultsWindow(self)
        self.shown = False
        key_binding_mgr.add_binding('<Mod4>space', self.toggle)

    def main(self):
        gtk.gdk.threads_init()
        key_binding_mgr.start()
        def _sig_handler(signum, frame):
            print 'Ctrl-C pressed!!!'
            sys.exit(0)
        signal.signal(signal.SIGINT, _sig_handler)
        gtk.main()

    def show(self):
        self.results_window.show()
        self.shown = True
        return gtk.Window.show(self)

    def toggle(self):
        if self.shown:
            self.hide()
        else:
            self.show()


    def hide(self):
        self.results_window.hide()
        self.shown = False
        return gtk.Window.hide(self)

    def do_realize(self):
        #r = gtk.gdk.Region()
        #widget.window.input_shape_combine_region(r, 0, 0)
        #print 'Result:', gtk.gdk.keyboard_grab(self.window)
        gtk.Window.do_realize(self)
        self.window.focus()
        pass

    def searchbox_changed(self, widget, event=None):
        from utils import search_strings
        text = widget.get_text()

        def do_lookup(text):
            if text:
                for k in self.commands:
                    if text.startswith(k + ' '):
                        arg_text = text[len(k) + 1:]
                        results = self.commands[k].lookup(arg_text)
                        print results
                        break
                else:
                    results = [{
                        'title': self.commands[c].nice_name,
                        'caption': self.commands[c].caption,
                        'callback': self.commands[c].execute,
                        'thumbnail': self.commands[c].icon
                    } for c in search_strings(text, self.commands.keys())]
                    results.extend(self.commands['launch'].lookup(text))
            else:
                results = []
            self.results_window.update_results(results)

        # Make sure calling lookup doesn't block the main searchbox draw.
        gobject.idle_add(do_lookup, text, priority=gobject.PRIORITY_LOW)




    def do_screen_changed(self, old_screen=None):
        screen = self.get_screen()
        colormap = screen.get_rgba_colormap()
        if colormap == None:
            print 'Your screen does not support alpha channels!'
            colormap = screen.get_rgb_colormap()
            self.supports_alpha = False
        else:
            print 'Your screen supports alpha channels!'
            self.supports_alpha = True

        self.set_colormap(colormap)

        return True


    def draw_window(self, widget, event, type="key"):
        c = widget.window.cairo_create()
        #Make the window transparent
        width = widget.get_allocation().width
        height = widget.get_allocation().height

        c.set_source_rgba(0.0, 0.0, 0.0, 0.0)
        c.set_operator(cairo.OPERATOR_SOURCE)
        c.paint()

        c.set_operator(cairo.OPERATOR_OVER)

        self.pg = pangocairo.CairoContext(c)
        self.pgl = self.pg.create_layout()
        self.pgl.set_width(gtk.gdk.screen_get_default().get_width() * pango.SCALE)
        pgfont = pango.FontDescription("sans 28")
        pgfont.set_family("Droid Sans")
        self.pgl.set_font_description(pgfont)

        text = markup_escape_text(self._searchbox.get_text())
        self.pgl.set_markup('<span letter_spacing="-1000">%s</span>' % text)
        cursor_pos = _char_offset_to_byte_offset(self._searchbox.get_position(), text)


        #sort out selected text
        try:
            selected = self._searchbox.get_selection_bounds()
            selected_1_pos = self.pgl.get_cursor_pos(_char_offset_to_byte_offset(selected[0], text))[0]
            selected_2_pos = self.pgl.get_cursor_pos(_char_offset_to_byte_offset(selected[1], text))[0]
        except IndexError:
            selected_1_pos = None

        (pglw, pglh) = self.pgl.get_pixel_size()
        print pglw, pglh

        width = max(120, pglw + 80)
        height = max(120, pglh + 80)
        widget.resize(width, height)

        pglx = (width / 2) - (pglw / 2)
        pgly = (height / 2) - (pglh / 2)
        print pglx, pgly

        c.set_source_rgba(0.0, 0.0, 0.0, 0.7)
        rounded_rectangle(c, 20, 20, width - 40, height - 40, 10, 10)
        c.fill()

        rounded_rectangle(c, 20, 20, width - 40, height - 40, 10, 10)
        c.set_source_rgba(0.2, 0.2, 0.2, 0.7)
        c.stroke()

        if selected_1_pos is not None:
            c.set_source_rgba(1, 1, 1, 0.1)
            selected_w = (selected_2_pos[0] - selected_1_pos[0]) / pango.SCALE
            rounded_rectangle(c, selected_1_pos[0] / pango.SCALE + pglx - 5, selected_1_pos[1] / pango.SCALE + pgly - 5, selected_w + 10,
                              selected_1_pos[3] / pango.SCALE + 10, 5, 5)
            c.fill()
        c.set_source_rgb(1, 1, 1)
        c.move_to(pglx, pgly)
        self.pg.update_layout(self.pgl)
        self.pg.show_layout(self.pgl)

        # Draw the cursor
        if len(text) and cursor_pos != len(text):
            cursor_pos = self.pgl.get_cursor_pos(cursor_pos)[0]
            c.set_source_rgba(1, 1, 1, 0.7)
            c.rectangle(cursor_pos[0] / pango.SCALE + pglx, cursor_pos[1] / pango.SCALE + pgly, 1, cursor_pos[3] / pango.SCALE)
            c.fill()