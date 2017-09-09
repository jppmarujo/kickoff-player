import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')

from gi.repository import Gtk, Gst, GObject
from helpers.gtk import add_widget_class

Gst.init(None)


class GstBox(Gtk.Box):

  __gtype_name__ = 'GstBox'

  callback = GObject.property(type=object, flags=GObject.PARAM_READWRITE)

  def __init__(self, *args, **kwargs):
    Gtk.Box.__init__(self, *args, **kwargs)

    self.restart = False
    self.buffer  = 0

    self.gtksink = Gst.ElementFactory.make('gtksink')
    self.swidget = self.gtksink.props.widget
    self.pack_start(self.swidget, True, True, 0)

    self.playbin = Gst.ElementFactory.make('playbin')
    self.playbin.set_property('video-sink', self.gtksink)
    self.playbin.set_property('force-aspect-ratio', True)

    self.dbus = self.playbin.get_bus()
    self.dbus.add_signal_watch()
    self.dbus.connect('message', self.on_dbus_message)

    add_widget_class(self, 'player-video')

  def get_state(self):
    state = self.playbin.get_state(1)
    state = list(state)[1]
    state = state.value_name.split('_')[-1]

    return state

  def open(self, url):
    self.playbin.set_state(Gst.State.NULL)
    self.playbin.set_property('uri', url)

  def play(self):
    if self.get_state() != 'PLAYING':
      self.playbin.set_state(Gst.State.PLAYING)
      self.callback('PLAYING')

  def pause(self):
    if self.get_state() != 'PAUSED':
      self.playbin.set_state(Gst.State.PAUSED)
      self.callback('PAUSED')

  def stop(self):
    if self.get_state() != 'NULL':
      self.playbin.set_state(Gst.State.NULL)
      self.callback('NULL')

  def set_volume(self, volume):
    self.playbin.set_property('volume', volume)

  def buffer(self, message):
    self.buffer = int(message.parse_buffering())
    self.callback("%s %s%s" % ('Buffering', self.buffer, '%'))

    if self.get_state() != 'PAUSED':
      self.playbin.set_state(Gst.State.PAUSED)

  def restart(self):
    self.restart = True
    self.callback('BUFFER')
    self.playbin.set_state(Gst.State.NULL)

  def resume(self):
    if self.restart and self.buffer == 0:
      self.restart = False
      self.play()

    if self.buffer == 100 and not self.restart:
      self.buffer = 0
      self.play()

  def close(self):
    self.callback('ERROR')
    self.playbin.set_state(Gst.State.NULL)

  def on_dbus_message(self, _bus, message):
    if message.type == Gst.MessageType.BUFFERING:
      self.buffer(message)
    elif message.type == Gst.MessageType.EOS:
      self.restart()
    elif message.type == Gst.MessageType.ERROR:
      self.close()
    else:
      self.resume()
