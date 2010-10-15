#!/usr/bin/python
# coding: UTF-8


import Xlib.X
import rb
import os
from time import sleep
import Xlib
import Xlib.display
import gobject
import gtk
import glib
import urllib

# TODO:
#   - allow hotkey to be configured via gconf
#       -> process keysyms (https://www.siafoo.net/snippet/239)

class DeleteFilePlugin (rb.Plugin):
    # Mod4+Up
    delete_key = 111
    delete_mask = 0x40

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
    shell = None

    doListen = False

    # init plugin
    def __init__(self):
        rb.Plugin.__init__(self)

    # register hotkey, tell X that we want keyrelease events and start listening
    def activate(self, shell):
        self.display = Xlib.display.Display()
        self.root = self.display.screen().root
        self.display.allow_events(Xlib.X.AsyncKeyboard, Xlib.X.CurrentTime)
        self.root.change_attributes(event_mask = Xlib.X.KeyReleaseMask)
        self.shell = shell
        self.register_hotkey()
        self.doListen = True
        gobject.timeout_add(300, self.listen_cb)

    # stop listening, unregister hotkey and clean up
    def deactivate(self, shell):
        self.doListen = False
        self.unregister_hotkey()
        self.display.close()

    # register the hotkey
    def register_hotkey(self):
        for modifier in self.modifier_combinations:
            self.root.grab_key(self.delete_key, modifier, True, Xlib.X.GrabModeAsync, Xlib.X.GrabModeAsync)

    # unregister the hotkey
    def unregister_hotkey(self):
        for modifier in self.modifier_combinations:
            self.root.ungrab_key(self.delete_key, modifier)


    # callback for listening, checks if the hotkey has been pressed
    def listen_cb(self):
        gtk.gdk.threads_enter()

        if(not self.doListen):
            gtk.gdk.threads_leave()
            return False

        if(self.root.display.pending_events() > 0 and self.doListen):
            event = self.root.display.next_event()
            if event.type == Xlib.X.KeyRelease and event.detail == self.delete_key:
                mask = event.state & ~(self.capslock_mask | self.numlock_mask | self.scrolllock_mask)
                if mask == self.delete_mask:
                    self.delete()

        gtk.gdk.threads_leave()
        return True

    # deletes the current playing file
    def delete(self):
        file = self.shell.props.shell_player.get_playing_path()
        file = file.replace("file://", "")
        file = urllib.unquote(file)
        file = file.replace("\"", "\\\"")
        file = file.replace("$", "\\$")
        if(isinstance(file, str)):
            filename = file.rpartition("/")[2]
            
            notify = "notify-send -i \"user-trash-full\" \""+filename+"\""
            os.system(notify)
            try:
                self.shell.props.shell_player.do_next()
            except glib.GError:
                None

            os.system("trash \""+file+"\"")
            
