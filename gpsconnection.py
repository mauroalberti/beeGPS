#!/usr/bin/env python
""" GPS Receiver connection class - (C)2009 - Bob Bruce - Bob.Bruce@pobox.com
                                              www.hwps.ca
    see class documentation below.
"""

import time
import serial


class NoGPSConnected(Exception):
    
    def __init__(self, value):
        
        self.value = value
        
        
    def __str__(self):
        
        return self.value
    

class GPSPosition(object):
    """GPS Position Class
    
    Bob.Bruce@pobox.com - www.hwps.ca
    
    CLASS VARIABLES:
    datumEPSG = EPSG number of the datum (changed if a datum message is detected)
    datumSet = indicates that a proprietary message stating the datum was found
    hasFix = indicator of whether a fix was found
    latitude = latitude (float)
    latitudeNS = latitude N or S of equator
    longitude = longitude (float)
    longitudeEW = longitude E or W of PM
    numSatellites = number of satellites used for fix
    hdop = Horizontal Dilution Of Precision
    theDateTime = date & time of position
    fixQuality = 0 = fix not available
               = 1 = GPS fix
               = 2 = Differential GPS fix (i.e. WAAS correction)
    bearing = Track made good, degrees true
    speed = Speed over ground (km/hr)
    satelliteData = info on the satellites used for the position,
                  = a list of tuples as follows:
                  (satellite number, elevation in degrees, azimuth in degrees to true, SNR in dB)
    
    """
    
    def __init__(self):
        
        self.satelliteData = [] # this will be converted to a list of tuples
        self.hdop = 0.0 # accuracy isn't always provided in the message - this is default
        self.hasFix = False


class GPSConnection(object):
    """GPS Connection Class - finds and connects an NMEA 0183 input source
    from a SERIAL PORT.
    
    !!! Your GPS MUST BE SET TO OUTPUT NMEA MESSAGES ON THE SERIAL PORT FOR THIS
    CLASS TO WORK !!!
    
    GPS receiver is connected as follows:
            Baud rate: 4800
            Number of data bits: 8 (bit 7 is 0)
            Stop bits: 1 (or more)
            Parity: none
            Handshake: none
        (based on the document: "The NMEA 0183 Protocol" by Klaus Betke)
        other NMEA 0183 references:
            http://www.gpsinformation.org/dale/nmea.htm
            http://gpsd.berlios.de/NMEA.txt
    
    uses the Python Serial Port Extension (pyserial) available
        http://sourceforge.net/projects/pyserial/ - you must have this in the
        /python25/lib/site-packages folder in order for this class to work.
    
    CLASS VARIABLES:
    connected = returns a boolean value indicating whether a GPS connection is found
                True means a GPS receiver is connected
    serialPort = connected serial port object
    hasFix = boolean = indicates whether a valid position is obtained and stored
    
    METHODS:
    __init__ = finds and connects the first GPS receiver attached to a serial port
    thePort = returns the port # that the receiver is connected to
    getPosition = returns a CSV string with the latitude and longitude in the
                  form: dd.ddddddd,A,ddd.ddddddd,A where the characters will be
                  N or S and E or W respectively
    getVelocity = returns the velocity in km/hr
    getBearing = returns the bearing 
    
    """
    
    def __init__(self):
        
        self.port = 0
        self.connected = False
        self.serialPort = 0
        self.readErrorLimit = 5
        self.readErrorCount = 0
        self.datumSet = False
        
        # currently only NAD83 and WGS84 LL datums are supported
        self.datums = {'NAD83': 4269, 'WGS 84': 4326}
        self.datumEPSG = 4326
        
        self.baudRates = [1200, 2400, 4800, 9600, 14400, 28800, 36400, 56700]
        
        
    def connectPort(self):
        """
        Method cycles through port numbers from 0 to 18 and baud rates shown below to attempt
        a connection. If a connection to a serial port was made then self.connected is set to
        True otherwise it is false.
        
        These class variables are set:
            self.connected = indicator whether a connection to a port was successful
            self.port = the port # that is connected
            self.serialPort = the serial.Serial object that is the connected port
            self.portName = the name of the connected serial port (i.e. COM1)            
        """
        
        self.port = 0
        self.portName = ''
        self.port_maxval = 18

        while(not self.connected and self.port < self.port_maxval):
            for self.baudRate in self.baudRates:
                self.tryConnectPortSpeed(self.port,self.baudRate)
                if self.connected: # are connected, stop trying baud rates to connect on
                    print 'Got GPS on port ' + str(self.port) + ' ' + self.serialPort.portstr
                    break
            else:
                if self.port >= self.port_maxval:
                    break
                else:
                    self.port += 1
                    
            if self.connected:
                break # got connected, break out of while loop
        
        if self.connected: 
            self.portName = self.serialPort.portstr
        else: 
            raise NoGPSConnected("Could not find a GPS Serial Connection sending NMEA messages!")
        
        
    def connectPortBySettings(self, portNumber, portSpeed):
        """
        Attempts to connect a specified port at a specified speed. If a connection was made then
        self.connected is set to True otherwise it is false and an error condition is raised.

        Input Parameters:
        portNumber = the number of the serial port to connect (0,1,...,18)
        portSpeed = the index to the speed in the list self.baudRates
        
        These class variables are set:
            self.connected = indicator whether a connection to a port was successful
            self.port = the port # that is connected
            self.serialPort = the serial.Serial object that is the connected port
            self.portName = the name of the connected serial port (i.e. COM1)            
        """
        
        self.port = portNumber
        self.portName = ''
        self.baudRate = self.baudRates[portSpeed]

        self.tryConnectPortSpeed(self.port,self.baudRate)
        if self.connected: 
            self.portName = self.serialPort.portstr
        else: 
            raise NoGPSConnected("Could not find a GPS Serial Connection sending NMEA messages on port: COM" +
                                   str(self.port+1) + " at speed " + str(self.baudRate) + "!")
        
    def tryConnectPortSpeed(self,port,baudRate):
        """
        Method uses input port number and baud rate to attempt a connection. If a connection
        to a serial port was made then self.connected is set to True otherwise it is false.
        
        These class variables are set:
            self.connected = indicator whether a connection to a port was successful
            self.port = the port # that is connected
            self.serialPort = the serial.Serial object that is the connected port
            self.portName = the name of the connected serial port (i.e. COM1)            
        """
        try:
            self.serialPort = serial.Serial(port, baudRate, timeout=.25, parity=serial.PARITY_NONE)
            self.serialPort.open()
            
            for i in range(10): # look for a NMEA message string from the serial port
                aline = self.serialPort.readline()
                if aline[:3] == '$GP':
                    self.connected = True
                    break # got a NMEA message stop reading messages
            else: # didn't get a NMEA message try next baud rate
                self.serialPort.close()
                del(self.serialPort)
                
        except serial.serialutil.SerialException, e:
            # print 'Failed to connect on port ' + str(self.port) + ' at rate: '\
            #    + str(self.baudRate) + ' ',e
            pass # leave exception alone, move on to next baud rate
        
        except: 
            pass # some other exception in connecting


    def getPosition(self):
        """
        Gets all of the data available from the GPS messages including the position and
        its quality, the satellites that are available and the course and speed.
        
        Returns current position from GGA GPS message in the format: 'dd.ddddddd,N,ddd.ddddddd,W'
        where N and W will indicate N or S of equator, W or E of prime meridian. The rest of the
        information can be obtained via the class variables.
        
        stores class variables as follows:
            self.hasFix = True or False = got an actual position
            self.latitude = latitude (float)
            self.latitudeNS = latitude N or S of equator
            self.longitude = longitude (float)
            self.longitudeEW = longitude E or W of PM
            self.numSatellites = number of satellites used for fix
            self.hdop = measure of horizontal accuracy
            self.theDateTime = date & time of position
            self.fixQuality = 0 = fix not available
                            = 1 = GPS fix
                            = 2 = Differential GPS fix
            self.bearing = Track made good, degrees true
            self.speed = Speed over ground (km/hr)
            self.satelliteData = info on the satellites used for the position,
                               = a list of tuples as follows:
                               (satellite number, elevation in degrees, azimuth in degrees to true, SNR in dB)
        """
        
        self.hasFix = False
        hasBearing = False
        hasSatellites = False
        numSatellites = 0
        
        thePosition = GPSPosition()
        
        aline = ''
        theIndex = 0
        iSat = 0
        for i in range(20): # look at 20 lines to acquire all of the data
            try:
                aline = self.serialPort.readline()
            except Exception:
                self.readErrorCount += 1
                if self.readErrorCount > self.readErrorLimit:
                    self.connected = False
                    self.serialPort.close()
                    raise NoGPSConnected("Lost connection to GPS!")
                
            if aline[:6] == '$GPGGA':
                try:
                    parts = aline.split(',')
                    if parts[2] == '' or parts[4] == '': break # latitude or longitude is blank
                    thePosition.hasFix = True
                    thePosition.datumEPSG = self.datumEPSG
                    thePosition.latitude = float(parts[2][:2]) + float(parts[2][2:])/60.0
                    thePosition.latitudeNS = parts[3]
                    thePosition.longitude = float(parts[4][:3]) + float(parts[4][3:])/60.0
                    thePosition.longitudeEW = parts[5]
                    thePosition.fixQuality = parts[6]
                    thePosition.numSatellites = int(parts[7])
                    if parts[8] != '': 
                        thePosition.hdop = float(parts[8])
                    atime = time.localtime()
                    thePosition.theDateTime = str(atime[0]) + "-" + str(atime[1]) + "-" + str(atime[2]) + " " +\
                        str(atime[3]) + ":" + str(atime[4]) + ":" + str(atime[5])
                    # thePosition.timeUTC = parts[1][:2] + ':' + parts[1][2:4] + ':' + parts[1][4:]
                    if hasBearing and hasSatellites: 
                        break
                except Exception, e:
                    pass # $GPGGA message was corrupted, ignore and carry on
                
            elif aline[:6] == '$GPRMC':
                try:
                    # 1 Knot = 1.852 Kilometers per Hour from: http://www.calculateme.com/Speed/Knots/ToKilometersperHour.htm
                    parts = aline.split(',')
                    thePosition.bearing = float(parts[8])
                    thePosition.speed = float(parts[7]) * 1.852
                    hasBearing = True
                    if self.hasFix and hasSatellites: 
                        break
                except Exception, e:
                    thePosition.bearing = 0.0
                    thePosition.speed = 0.0
                    # $GPRMC message was corrupted, ignore and carry on
                    
            elif aline[:6] == '$GPGSV': # process Satellites in view message
                try:
                    parts = aline.split(',')
                    numSatInMess = (len(parts) - 4)/4
                    for iSat in range(numSatInMess):
                        theIndex = 4 * iSat
                        if iSat == numSatInMess - 1: # special processing for last satellite in message - remove checksum
                            thePosition.satelliteData.append((parts[theIndex+4], parts[theIndex+5], parts[theIndex+6],\
                                                   parts[theIndex+7].split('*')[0]))
                        else:
                            thePosition.satelliteData.append((parts[theIndex+4], parts[theIndex+5], parts[theIndex+6],\
                                                   parts[theIndex+7]))
                    if parts[1] == parts[2]: 
                        hasSatellites = True # have processed last satellite message
                    if thePosition.hasFix and hasBearing and hasSatellites: break
                except Exception, e:
                    pass # $GPGSV message was corrupted, ignore and carry on
                
            elif aline[:6] == '$PGRMM' and not self.datumSet: # process GARMIN proprietary message containing datum
                try:
                    self.datumSet = True
                    parts = aline.split(',')
                    thedatum = parts[1].split('*')[0]
                    default = 4326
                    self.datumEPSG = self.datums.get(thedatum,default)
                except Exception, e:
                    pass # $GPGSV message was corrupted, ignore and carry on
                
        return thePosition
