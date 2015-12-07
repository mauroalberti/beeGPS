
from trackGps import trackGps

def name():
    return "beeGPS - adapted from trackGps - for Windows"

def description():
    return "Track your GPS location using GPSConnection"

def version():
    return "2.0.1"

def qgisMinimumVersion():
    return "2.0"

def authorName():
    return "JJL <Buggerone@gmail.com> & \
            Bob Bruce<Bob.Bruce@pobox.com> & \
            Mauro Alberti <alberti.m65@gmail.com>"

def classFactory(iface):
    return trackGps(iface)
