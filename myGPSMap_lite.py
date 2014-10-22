#!/usr/bin/python

"""
Copyright (C) Hadley Rich 2008 <hads@nice.net.nz>
based on main.c - with thanks to John Stowers

This is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License
as published by the Free Software Foundation; version 2.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, see <http://www.gnu.org/licenses/>.
"""

import sys
import os.path
import random
from math import pi
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GObject
import socket
import struct
import select
import threading


GObject.threads_init()
Gdk.threads_init()

from gi.repository import OsmGpsMap as osmgpsmap
print "using library: %s (version %s)" % (osmgpsmap.__file__, osmgpsmap._version)

assert osmgpsmap._version == "1.0"

class DummyMapNoGpsPoint(osmgpsmap.Map):
    def do_draw_gps_point(self, drawable):
        pass
GObject.type_register(DummyMapNoGpsPoint)

class DummyLayer(GObject.GObject, osmgpsmap.MapLayer):
    def __init__(self):
        GObject.GObject.__init__(self)

    def do_draw(self, gpsmap, gdkdrawable):
        pass

    def do_render(self, gpsmap):
        pass

    def do_busy(self):
        return False

    def do_button_press(self, gpsmap, gdkeventbutton):
        return False
GObject.type_register(DummyLayer)

class UI(Gtk.Window):
    def __init__(self,UDPClient):       

        Gtk.Window.__init__(self, type=Gtk.WindowType.TOPLEVEL)

        self.set_default_size(500, 500)
        self.connect('destroy', lambda x: Gtk.main_quit())
        self.connect('delete_event',self.delete_event)
        self.set_title('myGPSMap for Arduino connection')

        self.vbox = Gtk.VBox(False, 0)
        self.add(self.vbox)

        if 0:
            self.osm = DummyMapNoGpsPoint()
        else:
            self.osm = osmgpsmap.Map()
        self.osm.layer_add(
                    osmgpsmap.MapOsd(
                        show_dpad=True,
                        show_zoom=True,
                        show_crosshair=False)
        )
        self.osm.props.show_trip_history = False
        self.osm.set_center_and_zoom(48.824094, 9.062013, 20)      
        self.osm.gps_add(48.824094, 9.062013, heading=0.1*360)
        self.osm.layer_add(
                    DummyLayer()
        )

        self.last_image = None

        self.osm.connect('button_press_event', self.on_button_press)
#        self.osm.connect('button_release_event', self.on_button_release)

        #connect keyboard shortcuts
        self.osm.set_keyboard_shortcut(osmgpsmap.MapKey_t.FULLSCREEN, Gdk.keyval_from_name("F11"))
        self.osm.set_keyboard_shortcut(osmgpsmap.MapKey_t.UP, Gdk.keyval_from_name("Up"))
        self.osm.set_keyboard_shortcut(osmgpsmap.MapKey_t.DOWN, Gdk.keyval_from_name("Down"))
        self.osm.set_keyboard_shortcut(osmgpsmap.MapKey_t.LEFT, Gdk.keyval_from_name("Left"))
        self.osm.set_keyboard_shortcut(osmgpsmap.MapKey_t.RIGHT, Gdk.keyval_from_name("Right"))

        zoom_in_button = Gtk.Button(stock=Gtk.STOCK_ZOOM_IN)
        zoom_in_button.connect('clicked', self.zoom_in_clicked)
        zoom_out_button = Gtk.Button(stock=Gtk.STOCK_ZOOM_OUT)
        zoom_out_button.connect('clicked', self.zoom_out_clicked)
        #home_button = Gtk.Button(stock=Gtk.STOCK_HOME)
        home_button = Gtk.Button("Home")
        home_button.connect('clicked', self.home_clicked)
        cache_button = Gtk.Button('Cache')
        cache_button.connect('clicked', self.cache_clicked)

        self.vbox.pack_start(self.osm, True, True, 0)
        hbox = Gtk.HBox(False, 0)
        hbox.pack_start(zoom_in_button, False, True, 0)
        hbox.pack_start(zoom_out_button, False, True, 0)
        hbox.pack_start(home_button, False, True, 0)
        hbox.pack_start(cache_button, False, True, 0)

        cb = Gtk.CheckButton("Disable Cache")
        cb.props.active = False
        cb.connect("toggled", self.disable_cache_toggled)
        self.vbox.pack_end(cb, False, True, 0)

        self.vbox.pack_end(hbox, False, True, 0)

        GObject.timeout_add(500, self.print_tiles)
        
        self.udpClient = UDPClient
        self.listenerThread = MyThread(self.osm,self.udpClient)
        self.listenerThread.start()

    def delete_event(self,widget,event,data=None):
        #print "delete signal occurred"
        Gtk.main_quit()
        self.listenerThread.quit = True
        udpClient.close()
        return False

    def disable_cache_toggled(self, btn):
        if btn.props.active:
            self.osm.props.tile_cache = osmgpsmap.MAP_CACHE_DISABLED
        else:
            self.osm.props.tile_cache = osmgpsmap.MAP_CACHE_AUTO

#    def on_show_tooltips_toggled(self, btn):
#        self.show_tooltips = btn.props.active

    def load_map_clicked(self, button):
        uri = self.repouri_entry.get_text()
        format = self.image_format_entry.get_text()
        if uri and format:
            if self.osm:
                #remove old map
                self.vbox.remove(self.osm)
            try:
                self.osm = osmgpsmap.Map(
                    repo_uri=uri,
                    image_format=format
                )
            except Exception, e:
                print "ERROR:", e
                self.osm = osm.Map()

            self.vbox.pack_start(self.osm, True, True, 0)
            self.osm.connect('button_release_event', self.map_clicked)
            self.osm.show()

    def print_tiles(self):
        if self.osm.props.tiles_queued != 0:
            print self.osm.props.tiles_queued, 'tiles queued'
        return True

    def zoom_in_clicked(self, button):
        self.osm.set_zoom(self.osm.props.zoom + 1)
 
    def zoom_out_clicked(self, button):
        self.osm.set_zoom(self.osm.props.zoom - 1)

    def home_clicked(self, button):
        self.osm.set_center_and_zoom(48.823732, 9.060301, 16)
 
    def cache_clicked(self, button):
        bbox = self.osm.get_bbox()
        self.osm.download_maps(
            *bbox,
            zoom_start=self.osm.props.zoom,
            zoom_end=self.osm.props.max_zoom
        )

    def on_button_press(self, osm, event):
        state = event.get_state()
        lat,lon = self.osm.get_event_location(event).get_degrees()

        left = event.button == 1
        middle = event.button == 2 or (event.button == 1 and state & Gdk.ModifierType.SHIFT_MASK)
        right = event.button == 3 or (event.button == 1 and state & Gdk.ModifierType.CONTROL_MASK)

        #work around binding bug with invalid variable name
        GDK_2BUTTON_PRESS = getattr(Gdk.EventType, "2BUTTON_PRESS")
        GDK_3BUTTON_PRESS = getattr(Gdk.EventType, "3BUTTON_PRESS")

        if event.type == GDK_3BUTTON_PRESS:
            if middle:
                if self.last_image is not None:
                    self.osm.image_remove(self.last_image)
                    self.last_image = None
        elif event.type == GDK_2BUTTON_PRESS:
            if left:
                self.osm.gps_add(lat, lon, heading=random.random()*360)
                self.osm.set_center(lat,lon)
            if middle:
                pb = GdkPixbuf.Pixbuf.new_from_file_at_size ("poi.png", 24,24)
                self.last_image = self.osm.image_add(lat,lon,pb)
            if right:
                pass


class MyThread(threading.Thread):
    def __init__(self, osm, udpclient):
        super(MyThread, self).__init__()
        self.osm = osm
        self.udpClient = udpclient
        self.quit = False

    def update_osm(self, message):
        # print "updating..."
        lat = message[0]/1000000.0
        lon = message[1]/1000000.0
        heading = message[3]/100.0
        self.osm.gps_add(lat, lon, heading)
        self.osm.set_center(lat,lon)
        return False

    def run(self):
        while not self.quit:
            try:
                self.udpClient.connect()
            except:
                print "Cannot connect."
            try:
                while not self.quit:
                    result = select.select([self.udpClient.client],[],[])
                    data = result[0][0].recv(udpClient.bufferSize)
                    message = struct.unpack("<llLLcc",data)
                    print(message)
                    GObject.idle_add(self.update_osm, message)
            except:
                print "Cannot receive message"
        print "exited"

class UDPClient:
    def __init__(self, IPAddress, portNumber):
        self.IPAddress = IPAddress
        self.portNumber = portNumber
        self.bufferSize = 18

        self.client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def connect(self):
        try:
            self.client.bind((self.IPAddress, self.portNumber))
            self.client.setblocking(0)
        except: print "Cannot connect."

    def close(self):
        try:
            self.client.shutdown()
            self.client.close()
        except:
            pass


if __name__ == "__main__":

    udpClient = UDPClient("192.168.1.13", 1313)
    u = UI(udpClient)
    u.show_all()
    if os.name == "nt": Gdk.threads_enter()
    Gtk.main()
    if os.name == "nt": Gdk.threads_leave()
