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
from go.keybindings import KeyBindingManager
import signal

key_binding_mgr = KeyBindingManager()

RESOURCES_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'resources'))
def rounded_rectangle(cr, x, y, w, h, radius_x=5, radius_y=5):
	"""Draw a rectangle with rounded corners according to radius_x and radius_y."""
	# Following code is from http://www.cairographics.org/cookbook/roundedrectangles/
	ARC_TO_BEZIER = 0.55228475
	if radius_x > w - radius_x:
		radius_x = w / 2
	if radius_y > h - radius_y:
		radius_y = h / 2

	#approximate (quite close) the arc using a bezier curve
	c1 = ARC_TO_BEZIER * radius_x
	c2 = ARC_TO_BEZIER * radius_y

	cr.new_path()
	cr.move_to( x + radius_x, y)
	cr.rel_line_to(w - 2 * radius_x, 0.0)
	cr.rel_curve_to(c1, 0.0, radius_x, c2, radius_x, radius_y)
	cr.rel_line_to(0, h - 2 * radius_y)
	cr.rel_curve_to(0.0, c2, c1 - radius_x, radius_y, -radius_x, radius_y)
	cr.rel_line_to(-w + 2 * radius_x, 0)
	cr.rel_curve_to(-c1, 0, -radius_x, -c2, -radius_x, -radius_y)
	cr.rel_line_to(0, -h + 2 * radius_y)
	cr.rel_curve_to(0.0, -c2, radius_x - c1, -radius_y, radius_x, -radius_y)
	cr.close_path()

def _char_offset_to_byte_offset(offset, string):
            """Converts a logical character offset to a byte offset."""
            return len(str(unicode(string)[:offset]))

class GoResult(object):
    height = 56
    width = 420
    inner_space = 8
    spacing = 6
    image_size = 40
    title_font = pango.FontDescription('Droid Sans 13')
    caption_font = pango.FontDescription('Droid Sans 10')

    def __init__(self, title, caption=None, thumbnail=None, callback=None, x=0, y=0):
        self.title = title
        self.caption = caption
        self.thumbnail = thumbnail
        self.callback = callback
        self._thumbnail = None
        self.x = x
        self.y = y
        if self.thumbnail is not None and not isinstance(self.thumbnail, gtk.gdk.Pixbuf):
            self._thumbnail_loader = gtk.gdk.PixbufLoader()
            def _pb_loader_size_prepared(pb_loader, width, height):
                if height > width:
                    new_w = self.image_size
                    new_h = height * (self.image_size / width)
                else:
                    new_h = self.image_size
                    new_w = int(width * (float(self.image_size) / height))
                print 'Size:', new_h, new_w
                pb_loader.set_size(new_h, new_w)

            def _pb_loader_area_updated(pb_loader, x, y, width, height):
                self._thumbnail = cairo.ImageSurface(0, self.image_size, self.image_size)
                cr = cairo.Context(self._thumbnail)
                gtk_cr = gtk.gdk.CairoContext(cr)
                gtk_cr.set_source_pixbuf(pb_loader.get_pixbuf(), 0, 0)
                gtk_cr.paint()

            self._thumbnail_loader.connect('size-prepared', _pb_loader_size_prepared)
            self._thumbnail_loader.connect('area-updated', _pb_loader_area_updated)
            if isinstance(self.thumbnail, basestring):
                self._thumbnail_real = open(self.thumbnail, 'rb')
            else:
                self._thumbnail_real = self._thumbnail
            self._thumbnail_loader.write(self._thumbnail_real.read())
            self._thumbnail_loader.close()
        elif isinstance(self.thumbnail, gtk.gdk.Pixbuf):
            self._thumbnail = cairo.ImageSurface(0, self.image_size, self.image_size)
            cr = cairo.Context(self._thumbnail)
            gtk_cr = gtk.gdk.CairoContext(cr)
            gtk_cr.set_source_pixbuf(self.thumbnail, 0, 0)
            x = self.image_size / 2 - self.thumbnail.get_width() / 2
            y = self.image_size / 2 - self.thumbnail.get_height() / 2
            gtk_cr.rectangle(x, y, max(self.thumbnail.get_width(), self.image_size), max(self.thumbnail.get_height(), self.image_size))
            gtk_cr.fill()

        self.border_colour = [0.1, 0.1, 0.1, 0.75]
        self.border_width = 1
        self.background_colour = [0, 0, 0, 0.75]
        self.title_colour = [1, 1, 1, 1]
        self.caption_colour = [1, 1, 1, 0.5]
        self.thumbnail_opacity = 1.0
        self.opacity = 1.0

    def __hash__(self):
        return hash(sum((hash(self.title), hash(self.caption), hash(self.thumbnail), hash(self.callback))))

    def __cmp__(self, other):
        return isinstance(other, self.__class__) and hash(other) == hash(self)

    def draw(self, cr):
        x = self.x
        y = self.y
        background_colour = self.background_colour
        background_colour[3] *= self.opacity
        cr.set_source_rgba(*background_colour)
        rounded_rectangle(cr, x, y, self.width, self.height, 5, 5)
        cr.fill()
        cr.save()
        cr.set_operator(cairo.OPERATOR_SOURCE)
        rounded_rectangle(cr, x, y, self.width, self.height, 5, 5)
        border_colour = self.border_colour
        border_colour[3] *= self.opacity
        cr.set_source_rgba(*border_colour)
        cr.set_line_width(self.border_width)
        cr.stroke()
        cr.restore()
        if self._thumbnail is not None:
            cr.set_source_surface(self._thumbnail, x + self.inner_space, y + self.inner_space)
            cr.rectangle(x + self.inner_space, y + self.inner_space, 40, 40)
            cr.fill()
            text_space_left = x + self.image_size + self.inner_space * 2
        else:
            text_space_left = x + self.inner_space * 2
        pg = pangocairo.CairoContext(cr)

        pgl = pg.create_layout()
        pgl.set_font_description(self.title_font)
        pgl.set_markup(self.title)
        cr.move_to(text_space_left, y + self.inner_space)
        title_colour = self.title_colour
        title_colour[3] *= self.opacity
        cr.set_source_rgba(*title_colour)
        pg.show_layout(pgl)

        if self.caption is not None:
            pgl = pgl.copy()
            pgl.set_font_description(self.caption_font)
            pgl.set_markup(self.caption)
            cr.move_to(text_space_left, y + self.height - pgl.get_pixel_size()[1] - self.inner_space)
            caption_colour = self.caption_colour
            caption_colour[3] *= self.opacity
            cr.set_source_rgba(*caption_colour)

            pg.show_layout(pgl)

    def run(self, exec_string):
        gobject.idle_add(self.callback, exec_string)





class GoResultsWindow(gtk.Window):
    max_results = 4
    def __init__(self, go_window):
        gtk.Window.__init__(self)
        self.go_window = go_window
        self.results = []
        self.cursor_position = 0
        self.offset = 0
        self.last_cursor_position = None
        self.set_app_paintable(True)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_decorated(False)
        self.set_transient_for(self.go_window)
        self.set_default_size(420, 0)

        self._last_frame_time = None
        self.__drawing_queued = False
        self.tweener = Tweener(0.5, Easing.Cubic.ease_in_out)
        self.connect('expose-event', self.draw_window)
        self.do_screen_changed()

    @property
    def height(self):
        return self.get_allocation().height

    @property
    def width(self):
        return self.get_allocation().width

    def move_cursor(self, direction_or_newpos='down'):
        try:
            last = self.results[self.cursor_position]
        except IndexError:
            last = None
        reset = False
        if direction_or_newpos == 'down':
            newpos = self.cursor_position + 1
        elif direction_or_newpos == 'up':
            newpos = self.cursor_position - 1
        else:
            newpos = direction_or_newpos
            reset = True
        self.cursor_position = min(newpos, len(self.results) - 1)
        self.cursor_position = max(self.cursor_position, 0)
        try:
            selected = self.results[self.cursor_position]
        except IndexError:
            pass
        else:
            if selected is not last or reset == True:
                #    print 'Moving down!'
                #    for result in self.results:
                #        # how far between selected.real_y and where it needs to be?
                #        move_to = selected.real_y - self.height
                #        print 'Moving to %s - %s = %s' % (selected.real_y, self.height, move_to)
                #        self.tweener.add_tween(result, y=result.y + move_to, duration=0.25)
                #elif selected.real_y < self.get_allocation().y:
                #    print 'Moving up!'
                #    for result in self.results:
                #        self.tweener.add_tween(result, y=0 - (selected.real_y), duration=0.25)
                if selected.y + GoResult.height > self.height:
                    new_offset = max(0, self.cursor_position - 3) * (GoResult.height + GoResult.spacing)
                    try:
                        self.tweener.remove_tween(self._move_tween)
                    except AttributeError:
                        pass
                    self._move_tween = self.tweener.add_tween(self, offset=new_offset, duration=0.25)
                elif selected.y < self.get_allocation().y:
                    new_offset = self.cursor_position * (GoResult.height + GoResult.spacing)
                    try:
                        self.tweener.remove_tween(self._move_tween)
                    except AttributeError:
                        pass
                    self._move_tween = self.tweener.add_tween(self, offset=new_offset, duration=0.25)
                normal_border = GoResult('').border_colour
                normal_bg = GoResult('').background_colour
                for other in filter(lambda r: r is not selected, self.results):
                    other.border_colour = normal_border
                    self.tweener.add_tween(other, background_colour=normal_bg, duration=0.25)

                new_bg = selected.background_colour[:]
                new_bg[3] = 0.95
                selected.border_colour = [1, 1, 1, 1]
                if not reset:
                    self.tweener.add_tween(selected, background_colour=new_bg, duration=0.25)
                else:
                    selected.background_colour = new_bg
        self.redraw()


    def redraw(self):
        """Queue redraw. The redraw will be performed not more often than
           the `framerate` allows"""
        if self.__drawing_queued == False: #if we are moving, then there is a timeout somewhere already
            self.__drawing_queued = True
            self._last_frame_time = dt.datetime.now()
            gobject.timeout_add(1000 / 60, self.__interpolate)

    # animation bits
    def __interpolate(self):
        if self.tweener:
            self.tweener.update((dt.datetime.now() - self._last_frame_time).microseconds / 1000000.0)

        self.__drawing_queued = self.tweener.has_tweens()
        self._last_frame_time = dt.datetime.now()

        self.queue_draw() # this will trigger do_expose_event when the current events have been flushed
        return self.__drawing_queued

    def draw_window(self, widget, event, type="key"):
        c = widget.window.cairo_create()
        #Make the window transparent

        c.set_source_rgba(0.0, 0.0, 0.0, 0.0)
        c.set_operator(cairo.OPERATOR_SOURCE)
        c.paint()

        new_height = min(len(self.results), self.max_results) * (GoResult.height + GoResult.spacing)
        if self.height != new_height:
            self.resize(GoResult.width, new_height)

        c.set_operator(cairo.OPERATOR_OVER)
        c.rectangle(self.get_allocation().x, self.get_allocation().y, self.width, new_height)
        c.clip()
        x = 0
        for number, result in enumerate(self.results):
            y = (number * (GoResult.height + GoResult.spacing)) - self.offset
            result.x = x
            result.y = y
            #if self.cursor_position - 5 < number < self.cursor_position + 5:
            c.save()
            c.rectangle(x, y, GoResult.width, GoResult.height)
            c.clip()
            result.draw(c)
            c.restore()

    def update_results(self, new_results):
        new_results = [GoResult(r['title'], r.get('caption'), r.get('thumbnail'), r.get('callback')) for r in new_results[:]]
        #combined_results_len = len(self.results)
        #for result in new_results:
        #    if result not in self.results:
        #        combined_results_len += 1
        self.resize(GoResult.width, self.max_results * (GoResult.height + GoResult.spacing))
        x = gtk.gdk.screen_get_default().get_width() / 2 - GoResult.width / 2
        y = self.go_window.get_position()[1] + self.go_window.get_size()[1] + 20
        self.move(x, y)

        # TODO: add animation and scrolling
        self.results = new_results
        self.move_cursor(0)

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
        key_binding_mgr.add_binding('<Alt>space', self.toggle)

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
        c.set_source_rgba(1, 0.07, 0.07, 0.7)
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

if __name__ == '__main__':
    g = GoWindow()
    g.main()
