from go.utils.tweener import Tweener, Easing
from go.utils import rounded_rectangle
import gtk
import cairo
import pango
import pangocairo
from glib import markup_escape_text
import datetime as dt
from functools import partial
import gobject

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
                new_offset = None
                if selected.y + GoResult.height > self.height:
                    new_offset = max(0, self.cursor_position - 3) * (GoResult.height + GoResult.spacing)
                elif selected.y < self.get_allocation().y:
                    new_offset = self.cursor_position * (GoResult.height + GoResult.spacing)
                if new_offset is not None:
                    try:
                        pass
                    except AttributeError:
                        pass
                    self._move_tween = self.tweener.add_tween(self, offset=new_offset, duration=0.25, easing=Easing.Back.ease_out)
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
            if y <= self.height + GoResult.height and y + GoResult.height + GoResult.spacing >= 0:
                result.draw(c)
            else:
                print result.title
                print 'Y', y
                print 'offset', self.offset
                print 'height', self.height
                print
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