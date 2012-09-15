#!/usr/bin/python
# coding: UTF-8


import Xlib.X
from gi.repository import GObject, RB, Peas, GLib, Gdk, Notify
from urlparse import urlparse
from send2trash import send2trash
import os
import Xlib
import Xlib.display
import urllib

# TODO:
#   - allow hotkey to be configured via gconf
#       -> process keysyms (https://www.siafoo.net/snippet/239)
Gdk.threads_init()

class DeleteFilePlugin(GObject.Object, Peas.Activatable):
    __gtype_name__ = 'DeleteCurrentFilePlugin'
    object = GObject.property(type=GObject.Object)

    # Ctrl+'/'
    delete_key = 61
    delete_mask = 0x14

    numlock_mask = 0x10
    capslock_mask = 0x2
    scrolllock_mask = capslock_mask # TODO: unknown!

    modifier_combinations = (
        delete_mask,
        delete_mask | numlock_mask,
        delete_mask | scrolllock_mask,
        delete_mask | capslock_mask,
        delete_mask | numlock_mask | scrolllock_mask,
        delete_mask | numlock_mask | capslock_mask,
        delete_mask | scrolllock_mask | capslock_mask,
        delete_mask | numlock_mask | scrolllock_mask | capslock_mask)

    display = None
    root = None

    def __init__(self):
        '''
        init plugin
        '''
        super(DeleteFilePlugin, self).__init__()

    def do_activate(self):
        '''
        register hotkey, tell X that we want keyrelease events and start
        listening
        '''
        self.display = Xlib.display.Display()
        self.root = self.display.screen().root
        self.display.allow_events(Xlib.X.AsyncKeyboard, Xlib.X.CurrentTime)
        self.root.change_attributes(event_mask = Xlib.X.KeyReleaseMask)
        self.register_hotkey()
        self.listener_src = GObject.timeout_add(300, self.listen_cb)
        Notify.init('Delete Current File Plugin')

    def do_deactivate(self):
        '''
        stop listening, unregister hotkey and clean up
        '''
        GObject.source_remove(self.listener_src)
        self.unregister_hotkey()
        self.display.close()

    def register_hotkey(self):
        '''
        register the hotkey
        '''
        for modifier in self.modifier_combinations:
            self.root.grab_key(self.delete_key, modifier, True,
                    Xlib.X.GrabModeAsync, Xlib.X.GrabModeAsync)

    def unregister_hotkey(self):
        '''
        unregister the hotkey
        '''
        for modifier in self.modifier_combinations:
            self.root.ungrab_key(self.delete_key, modifier)

    def listen_cb(self):
        '''
        callback for listening, checks if the hotkey has been pressed
        '''
        Gdk.threads_enter()
        if self.root.display.pending_events() > 0:
            event = self.root.display.next_event()
            if event.type == Xlib.X.KeyRelease \
                    and event.detail == self.delete_key:
                self.delete()

        Gdk.threads_leave()
        return True

    def delete(self):
        '''
        Deletes the currently playing song
        '''
        sp = self.object.props.shell_player
        cur_entry = sp.get_playing_entry()
        if not cur_entry:
            return

        uri = urlparse(cur_entry.get_string(RB.RhythmDBPropType.LOCATION))
        if uri.scheme != 'file':
            return

        fPath = urllib.unquote(uri.path)
        notification = Notify.Notification.new('Rhythmbox',
                os.path.basename(fPath),
                'user-trash-full')
        notification.show()
        try:
            sp.do_next()
        except GLib.GError:
            pass

        send2trash(fPath)
