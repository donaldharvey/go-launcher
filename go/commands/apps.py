from go.commands import Command
from go.utils import search_non_contiguous_strings
from go.utils.multidict import MultiDict
from functools import partial
import gtk
import gio
import gmenu
import subprocess
class AppLaunchCommand(Command):
    name = 'launch'
    aliases = ['run']
    nice_name = 'Launch'
    caption = 'Launch an application.'

    def __init__(self):
        self.apps = MultiDict()
        menus = [gmenu.lookup_tree('applications.menu'), gmenu.lookup_tree('settings.menu')]
        map(lambda m: self._recurse_tree(m.root), menus)


    def exec_app(self, command, argv=''):
        print 'Launching %s!' % command
        subprocess.Popen(' '.join((command, argv)), shell=True)

    def lookup(self, search_string):
        if search_string == '':
            return []
        results = []
        for key in search_non_contiguous_strings(search_string, self.apps):
            for app in sorted(self.apps.getall(key)):
                results.append({
                    'title': app['name'],
                    'caption': app['comment'],
                    'thumbnail': app['icon'],
                    'callback': partial(self.exec_app, app['exec'])
                })
        return results

    def _pixbuf_from_icon(self, icon_string):
        try:
            gicon = gio.icon_new_for_string(icon_string)
            icon_theme = gtk.icon_theme_get_default()
            icon_info = icon_theme.lookup_by_gicon(gicon, 32, gtk.ICON_LOOKUP_USE_BUILTIN)
            icon = icon_info.load_icon()
            scaled_icon = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, 40, 40)
            scaled_icon.fill(0x00000000)
            icon.scale(scaled_icon, 4, 4, 32, 32, 4, 4, 32 / icon.get_width(), 32 / icon.get_height(), gtk.gdk.INTERP_BILINEAR)
            return scaled_icon
        except (AttributeError, TypeError, gio.Error):
           return None

    def _recurse_tree(self, tree):
        for item in tree.contents:
            if isinstance(item, gmenu.Entry):
                self.apps.add(item.name, {
                    'name': item.name,
                    'comment': item.comment,
                    'exec': item.get_exec(),
                    'icon': self._pixbuf_from_icon(item.icon)
                })
            elif isinstance(item, gmenu.Directory):
                self._recurse_tree(item)

commands = [AppLaunchCommand]