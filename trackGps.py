#!/usr/bin/python
# -*- coding: utf-8 -*-


"""
Adaptation of the original trackGps, downloaded from:
    http://svn.tuxfamily.org/viewvc.cgi/scrippets_scripts/trunk/qgis/trackGps/

Adapted by: Bob Bruce = Bob (dot) Bruce (at) pobox (dot) com
            www.hwps.ca

subsituted my GPSConnection class for the gpsd class 'cause gpsd doesn't work
on Windows. I try to make notes where major changes occur.
"""


import os, sys
from time import *
import datetime
import math
from decimal import Decimal

from PyQt4.QtCore import * 
from PyQt4.QtGui import *
from PyQt4 import uic
from qgis.core import *
from qgis.gui import *

from CanvasMarkers import PositionMarker
from gpsconnection import *
from gpstrackeroptions import GPSTrackerOptions
from shapefilenames import ShapeFileNames
from helpform import *



class ReadGpsd (QThread):
    """Thread that connects to GPSConnection and send read lat/lon to plugin interface"""
    
    def __init__ (self, parent=None, session=None):
        
        super(ReadGpsd,self).__init__(parent)
        self.session = GPSConnection()
        self.running = False
        self.tryAllPorts = True # by default all ports will be searched for a GPS device


    def setConnectionValues(self, portNumber, portSpeed):        
        
        if portSpeed in range(len(self.session.baudRates)) and portNumber in range(11,18):
            self.tryAllPorts = False # by default all ports will be searched for a GPS device
            self.portNumber = portNumber
            self.portSpeed = portSpeed
    
    
    def run(self):
        
        try:
            # open connection to gpsd
            # - old code - self.session = gps.gps(host="localhost", port="2947")
            if self.session.connected: # was connected and closed, just reopen
                self.session.serialPort.open()
                self.emit(SIGNAL("connectionMade()"))
            else: # not yet connected: find port and open it
                if self.tryAllPorts: 
                    self.session.search_available_port()
                else: 
                    self.session.connectPortBySettings(self.portNumber, self.portSpeed )
                self.emit(SIGNAL("connectionMade()"))
        except NoGPSConnected, e: # method search_available_port will issue this message if no NMEA GPS port is found
            self.emit(SIGNAL("connectionFailed(PyQt_PyObject)"),e)
            self.exit(1)

        # gather data from gpsd
        #QMessageBox.information(self.parent.mainWindow(),"ReadGpsd","Reached else part of run method!",QMessageBox.Ok)
        try:
            self.running = True
            while self.running and self.session.connected :
                #~ msg = "lat:%s\nlon:%s" % (self.session.fix.latitude,self.session.fix.longitude)
                #~ QMessageBox.information(self.iface.mainWindow(), "trackGps", msg)
                #~ print msg
                gpsPosition = self.session.getPosition()
                if gpsPosition.hasFix: 
                    self.emit(SIGNAL("readCoords(PyQt_PyObject)"),gpsPosition)
        except NoGPSConnected, e: # method search_available_port will issue this message if no NMEA GPS port is found
            self.emit(SIGNAL("connectionFailed(PyQt_PyObject)"),e)
            self.exit(1)
            
            
        self.quit()
    
    
    def stop(self):
        
        self.running = False
        self.wait(2000)
        self.session.serialPort.close()



class trackGps:
    
    def __init__(self, iface):

        # Save reference to the QGIS interface
        self.globalpath = os.path.dirname(os.path.abspath(__file__))
        self.iface = iface

        self.guiStarted = False # signal to destructor that this isn't actually been displayed yet        
        
        self.read = ReadGpsd(self.iface)
        
        # create dock widget from ui file
        print os.path.join(self.globalpath,"DockWidget.ui")
        self.dock = uic.loadUi(os.path.join(self.globalpath,"DockWidget.ui"))
        self.canvas = self.iface.mapCanvas()

        # Default options
        self.GPSSettings = QSettings()

        # indication that this is the first time for the plugin
        self.firstTime = self.GPSSettings.value("trackGpsGPSSettings/firstTime", True, type=bool)
        
        # index of marker for GPS position (this is the arrow)
        self.markerNumber = self.GPSSettings.value("trackGpsGPSSettings/markerNumber", 0, type=int)
        
        # default is black for marker fill color
        self.markerFillColor = QColor(self.GPSSettings.value("trackGpsGPSSettings/markerFillColor", QColor(0,0,0)))
        
        # default is yellow for marker outline color
        self.markerOutlineColor = QColor(self.GPSSettings.value("trackGpsGPSSettings/markerOutlineColor", QColor(255,255,0)))
        
        # width of tracking line
        self.trackLineWidth = self.GPSSettings.value("trackGpsGPSSettings/trackLineWidth", 3, type=int)
        
        # color of tracking line (default is red)
        self.lineColor = QColor(self.GPSSettings.value("trackGpsGPSSettings/lineColor", QColor(255,0,0)))
        
        self.saveInSHAPEFile = self.GPSSettings.value("trackGpsGPSSettings/saveInSHAPEFile", False, type=bool)
        
        # now recover/set the values for the serial port connection
        self.searchAllConnectionsSpeeds = self.GPSSettings.value("trackGpsGPSSettings/searchAllConnectionsSpeeds",
                                                                 True, type=bool)
        self.serialPortNumber = self.GPSSettings.value("trackGpsGPSSettings/serialPortNumber", 0, type=int)
        self.serialPortSpeed = self.GPSSettings.value("trackGpsGPSSettings/serialPortSpeed", 0, type=int)

        # set GPS connection values if they were recovered from a previous session
        if not self.searchAllConnectionsSpeeds: 
            self.read.setConnectionValues(self.serialPortNumber, self.serialPortSpeed)
        
        # initialize the graphic elements for the GPS position
        self.positionMarker = PositionMarker(self.canvas, self.markerNumber, self.markerFillColor, self.markerOutlineColor)
        self.rubberBand = QgsRubberBand(self.canvas)
        self.rubberBand.setColor(self.lineColor)
        self.rubberBand.setWidth(self.trackLineWidth)
        
        self.rubberBandS = []
        self.GPSPositions = [] # array of positions in current track
        self.GPSTracks = [] # array of all tracks

        
    def __del__(self):

        if self.guiStarted:
            
            # time to save plugin options as settings
            GPSSettings = QSettings()
            
            # indication that this is the first time for the plugin
            GPSSettings.setValue("trackGpsGPSSettings/firstTime", self.firstTime)
            GPSSettings.setValue("trackGpsGPSSettings/searchAllConnectionsSpeeds",
                                                                 bool(self.searchAllConnectionsSpeeds))
            GPSSettings.setValue("trackGpsGPSSettings/markerNumber", self.markerNumber)
            GPSSettings.setValue("trackGpsGPSSettings/markerFillColor", self.markerFillColor)
            GPSSettings.setValue("trackGpsGPSSettings/markerOutlineColor", self.markerOutlineColor)
            GPSSettings.setValue("trackGpsGPSSettings/trackLineWidth", self.trackLineWidth)
            GPSSettings.setValue("trackGpsGPSSettings/lineColor", self.lineColor)
            GPSSettings.setValue("trackGpsGPSSettings/saveInSHAPEFile", self.saveInSHAPEFile)
            GPSSettings.setValue("trackGpsGPSSettings/serialPortNumber", self.serialPortNumber)
            GPSSettings.setValue("trackGpsGPSSettings/serialPortSpeed", self.serialPortSpeed)
            GPSSettings.synch()
            QMessageBox.information(self.iface.mainWindow(),"Class trackGPS Ending","trackGPS is being destroyed!")

    
    def initGui(self):
        
        self.guiStarted = True # signal that the GPS dialog was displayed
        if self.firstTime:
            self.firstTime = False
            QMessageBox.information(self.iface.mainWindow(),"Track GPS location","Since this is the first time"+\
                                    " that you have used the 'Track GPS location' plugin please consult the help "+\
                                    "in the plugin menu")
            
        # Create actions for plugin
        self.actionStart = QAction(QIcon(":/plugins/trackgps/Satellite-22.png"), "Start GPS Tracking", self.iface.mainWindow())
        self.actionStart.setWhatsThis("Open GPS Connection and Start Tracking")
        self.actionStop  = QAction(QIcon(":/plugins/trackgps/Satellite-22.png"), "Stop GPS Tracking", self.iface.mainWindow())
        self.actionStop.setWhatsThis("Close the GPS Connection and Stop Tracking")
        self.actionOptions  = QAction(QIcon(":/plugins/trackgps/options.png"),"Set GPS Tracking Options", self.iface.mainWindow())
        self.actionOptions.setWhatsThis("Set the various GPS Connection/Tracking Options")
        
        # add help menu item
        self.helpAction = QAction(QIcon(":/plugins/trackgps/images/help-browser.png"), "GPS Tracking Help", self.iface.mainWindow())
     
        # New Track actions set up here
        self.dock.btnStartNewTrack.setDisabled(True) # Starting New Tracks is disabled at start
        QObject.connect(self.dock.btnStartNewTrack, SIGNAL("clicked()"), self.startNewTrack)
        
        # Connect the actions to its methods
        QObject.connect(self.actionStart, SIGNAL("activated()"), self.toogleGather)
        QObject.connect(self.actionStop,  SIGNAL("activated()"), self.toogleGather)
        QObject.connect(self.actionOptions,  SIGNAL("activated()"), self.showGPSMenuOptions)
        QObject.connect(self.dock.btnStart,  SIGNAL("clicked()"), self.toogleGather)
        QObject.connect(self.read,  SIGNAL("readCoords(PyQt_PyObject)"), self.setCoords)
        QObject.connect(self.read,  SIGNAL("connectionFailed(PyQt_PyObject)"), self.connectionFailed)
        QObject.connect(self.read,  SIGNAL("connectionMade()"), self.connectionMade)
        QObject.connect(self.helpAction, SIGNAL("activated()"), self.helpWindow)
     
        # Add menu items for action
        self.iface.addPluginToMenu("beeGPS", self.actionOptions)
        self.iface.addPluginToMenu("beeGPS", self.actionStart)
        self.iface.addPluginToMenu("beeGPS", self.helpAction)
        myPluginMenu = self.iface.pluginMenu()
        QObject.connect(myPluginMenu, SIGNAL("aboutToShow()"), self.updateTrackGPSMenu)
     
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dock)


    def helpWindow(self):
        
        window = HelpForm("TheQGISGPSTrackerPlugin.html",self.iface.mainWindow())
        window.show()
    
    
    def updateTrackGPSMenu(self):
        
        if self.read.running:
            self.iface.addPluginToMenu("beeGPS", self.actionStop)
            self.iface.removePluginMenu("beeGPS", self.actionStart)
        else:
            self.iface.addPluginToMenu("beeGPS", self.actionStart)
            self.iface.removePluginMenu("beeGPS", self.actionStop)
    
    
    def startNewTrack(self):
        
        self.read.stop() # close serial port
        self.rubberBandS.append(self.rubberBand)
        self.showGPSMenuOptions() # give user opportunity to change display options
        
        #if len(self.GPSPositions) > 0: # temporary section to display positional information
        #    QMessageBox.information(self.iface.mainWindow(),"trackGPS","There are: " + str(len(self.GPSPositions)) + " GPS Positions in the current track")
        #    for i in range(len(self.GPSPositions)):
        #        QMessageBox.information(self.iface.mainWindow(),"trackGPS","Position #" + str(i) + ": Latitude=" + str(self.GPSPositions[i].latitude))

        self.rubberBand=QgsRubberBand(self.canvas) # start new rubber band
        if len(self.GPSPositions) > 0 and self.saveInSHAPEFile:
            self.GPSTracks.append(self.GPSPositions) # save GPSPositions to GPSTracks
            self.GPSPositions = [] #reset of array contenent the current position
        self.startGather() # open serial port and record new track
       
       
    def unload(self):
        # Remove the plugin menu item
        
        self.iface.removePluginMenu("beeGPS", self.actionStart)
        self.iface.removePluginMenu("beeGPS", self.actionStop)
        self.iface.removePluginMenu("beeGPS", self.actionOptions)
    
    
    def startGather(self):
        #update all of the GPS display options
        
        self.positionMarker.markerNumber = self.markerNumber
        self.positionMarker.fillColor = self.markerFillColor
        self.positionMarker.outlineColor = self.markerOutlineColor
        self.rubberBand.setColor(self.lineColor)
        self.rubberBand.setWidth(self.trackLineWidth)
        self.positionMarker.show()
        
        # get destination crs of the canvas
        dest_crs = self.canvas.mapRenderer().destinationCrs()
        
        #print "destination crs:",dest_crs.description()
        # create transform object from WGS84 (GPS) to canvas CRS
        self.transform = QgsCoordinateTransform(QgsCoordinateReferenceSystem(self.read.session.datumEPSG,\
                                                        QgsCoordinateReferenceSystem.EpsgCrsId ),dest_crs)
        self.read.start()
        self.read.exec_()
    
    
    def setCoords(self, aGPSPosition):
    
        boolDistance = True
        boolTime = True
    
        #Controllo se è la prima acquisizione valutando la dimensione di GPSPosition[] a 0, in caso positivo acquisisco.
        if len(self.GPSPositions) == 0:
            self.GPSPositions.append(aGPSPosition)
            
        else:
            #Metodo tresholdAcquisition() per l'acquisizione dei punti "live" in base alla soglia di distanza che ritorna 
            #TRUE in caso la soglia sia stata superata, altrimenti FALSE
            boolDistance = self.tresholdAcquisition(aGPSPosition)
            
        #Controllo che tresholdAcquisition() abbia ritornato TRUE altrimenti passo al punto successivo
        if boolDistance == False:
            return
            
        #Metodo timeIntervals() per l'acquisizione dei punti "live" in base alla soglia di tempo che ritorna TRUE in caso
        #la soglia sia stata superata e acquisita, altrimenti FALSE
        boolTime = self.timeIntervals(aGPSPosition)
        
        #Controllo che timeIntervals() abbia ritornato TRUE altrimenti passo al punto successivo
        if boolTime == False:
          return
        
        else:
            self.GPSPositions.append(aGPSPosition)

        # display raw values
        self.dock.date.setText(aGPSPosition.theDateTime)
        self.dock.lat.setText(str(aGPSPosition.latitude) + ' ' + aGPSPosition.latitudeNS)
        self.dock.lon.setText(str(aGPSPosition.longitude) + ' ' + aGPSPosition.longitudeEW)
        self.dock.lineBearing.setText("%5.1i"%aGPSPosition.bearing)
        self.dock.lineSpeed.setText("%5.1i"%aGPSPosition.speed)
        self.dock.lineHDOP.setText(str(aGPSPosition.hdop))
        if aGPSPosition.fixQuality == 0:
            self.dock.lineQuality.setText("Fix not available")
        elif aGPSPosition.fixQuality == 1:
            self.dock.lineQuality.setText("GPS fix")
        else:
            self.dock.lineQuality.setText("Differential GPS fix") 
        
        # display arrow on the map
        latitude = aGPSPosition.latitude if aGPSPosition.latitudeNS == 'N' else aGPSPosition.latitude * -1.0
        longitude = aGPSPosition.longitude if aGPSPosition.longitudeEW == 'E' else aGPSPosition.longitude * -1.0
        p=self.transform.transform(QgsPoint(longitude, latitude))
        self.rubberBand.addPoint(p)
        self.positionMarker.setHasPosition(True)
        self.positionMarker.newCoords(p,aGPSPosition.bearing)
        
        doRefresh = False
        if doRefresh:
            # move map to keep marker at center
            curext = self.canvas.extent()
            p1 = QgsPoint(p.x() - curext.width()/2, p.y() - curext.height()/2)
            p2 = QgsPoint(p.x() + curext.width()/2, p.y() + curext.height()/2)
            self.canvas.setExtent(QgsRectangle (p1,p2))
            self.canvas.refresh()
    
    
    def stopGather(self):
        self.read.stop()
        self.positionMarker.hide()
        if len(self.GPSPositions) > 0: # and self.saveInSHAPEFile:
            self.GPSTracks.append(self.GPSPositions) # save GPSPositions to GPSTracks
                                                                                                                                    
        # if len(self.GPSTracks) > 0 and self.saveInSHAPEFile:
        if self.saveInSHAPEFile: # this is temporary
            # option to save SHAPE file is on, prompt for filename and write the tracks to the file
            self.makeShapeFiles()
            
        if len(self.GPSTracks) > 0:
            answer = QMessageBox.question(self.iface.mainWindow(),"Erase Tracks?","Erase the currently displayed tracks?",\
                                          QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer == QMessageBox.Yes:
                for band in self.rubberBandS:
                    band.reset()
                self.rubberBand.reset()
                self.canvas.refresh()
                self.rubberBandS = []
            self.GPSPositions = []
            self.GPSTracks = []
    
    
    def toogleGather(self):
        
        if self.read.running:
            QMessageBox.information(self.iface.mainWindow(),"GPS Tracker","Stopping GPS Tracking",QMessageBox.Ok)
            self.stopGather()
            self.dock.btnStart.setText("Start")
            self.dock.gpsInformation.setText("Gets GPS Receiver Information")
            self.dock.btnStartNewTrack.setDisabled(True)
        else:
            self.dock.btnStart.setText("Connecting, please be patient....")
            self.startGather()
            if self.read.session.connected: 
                self.dock.btnStart.setText("Stop")
    
    
    def connectionMade(self):
        
        # QMessageBox.information(self.iface.mainWindow(),"trackGps","GPS Receiver Connected on port: %s at %i baud\n"%\
        #                     (self.read.session.portName,self.read.session.baudRate),QMessageBox.Ok,0)
        
        self.dock.gpsInformation.setText("GPS Connected on port: %s at %i baud"%(self.read.session.portName,\
                                                                                          self.read.session.baudRate))
        self.dock.btnStart.setText("Stop")
        self.dock.btnStartNewTrack.setDisabled(False)
        
        # save connection values in session parameters
        self.serialPortNumber = self.read.session.port
        self.serialPortSpeed = self.read.session.baudRates.index(self.read.session.baudRate)
        self.searchAllConnectionsSpeeds = False
        
        
    def connectionFailed(self, msg):
        
        QMessageBox.warning(self.iface.mainWindow(),"beeGPS", "Connection to GPSConnection failed\n%s"%(msg),QMessageBox.Ok,0)
        if self.read.session.connected: 
            self.read.stop()
        self.dock.btnStart.setText("Start")
        self.dock.btnStartNewTrack.setDisabled(True) # Starting New Tracks is disabled at start
    
    
    def showGPSMenuOptions(self):

        myGPSOptionsDlg = GPSTrackerOptions(self)
        isOK = myGPSOptionsDlg.exec_()
        if isOK:
            if myGPSOptionsDlg.cbxMarkerType.currentIndex() != self.markerNumber: 
                self.markerNumber = myGPSOptionsDlg.cbxMarkerType.currentIndex()
            if myGPSOptionsDlg.lineColor != self.lineColor: 
                self.lineColor = myGPSOptionsDlg.lineColor
            if myGPSOptionsDlg.markerFillColor != self.markerFillColor: 
                self.markerFillColor = myGPSOptionsDlg.markerFillColor
            if myGPSOptionsDlg.markerOutlineColor != self.markerOutlineColor: 
                self.markerOutlineColor = myGPSOptionsDlg.markerOutlineColor
            if myGPSOptionsDlg.sbxTrackWidth.value() != self.trackLineWidth: 
                self.trackLineWidth = myGPSOptionsDlg.sbxTrackWidth.value()
            if myGPSOptionsDlg.cbxSaveGPSTrack.isChecked() != self.saveInSHAPEFile: 
                self.saveInSHAPEFile = myGPSOptionsDlg.cbxSaveGPSTrack.isChecked()
    
    
    def makeShapeFiles(self):

        myFileName = QgsProject.instance().fileName()
        myFileName = str(myFileName)
        # if this is a windows OS then the filename needs to have '/' converted to '\'
        if myFileName.find('windows') != 0 or myFileName.find('Windows') != 0: 
            myFileName = os.path.normpath(myFileName)
            
        myFilePath = os.path.dirname(myFileName)

        myShapeFileNamesDlg = ShapeFileNames(myFilePath)
        isOK = myShapeFileNamesDlg.exec_()
        CRS = QgsCoordinateReferenceSystem()
        crsIsOk = CRS.createFromOgcWmsCrs("EPSG:%d" % self.GPSTracks[0][0].datumEPSG)
        if not crsIsOk: 
            QMessageBox.warning(self.iface.mainWindow(),"trackGPS - makeShapeFiles","Error creating CRS from"+\
                                            " EPSG ID:" + str(self.GPSTracks[0][0].datumEPSG))
        if isOK and crsIsOk:
            if len(myShapeFileNamesDlg.lnePointsFileName.text()) > 0:
                # set up the fields for the Points SHAPE file
                box = QgsFields() 
                box.append(QgsField("LATITUDE", QVariant.Double , "Real", 9, 6)) 
                box.append(QgsField("LONGITUDE", QVariant.Double, "Real", 10, 6)) 
                box.append(QgsField("NUMOFSATS", QVariant.Int, "Integer", 2, 0))
                box.append(QgsField("HDOP", QVariant.Double, "Real", 4, 2))
                box.append(QgsField("DATETIME", QVariant.String, "String", 19, 0)) 
                box.append(QgsField("FIXTYPE", QVariant.String, "String", 1, 0))

                box.append(QgsField("BEARING", QVariant.Double, "Real", 6, 2))
                box.append(QgsField("SPEED-KPH", QVariant.Double, "Real", 5, 1)) 
                box.append(QgsField("TRACKNUM", QVariant.Int, "Integer", 2, 0))
                
                # set up the CRS
                # open the points SHAPE file
                pointsFile, fileOK = self.createSHAPEfile(myShapeFileNamesDlg.lnePointsFileName.text(),box,QGis.WKBPoint,CRS)
                if fileOK:
                    for j in range(len(self.GPSTracks)):
                        for i in range(len(self.GPSTracks[j])):
                            theFeature = QgsFeature()
                            latitude = self.GPSTracks[j][i].latitude
                            if self.GPSTracks[j][i].latitudeNS == 'S': 
                                latitude = -latitude
                            longitude = self.GPSTracks[j][i].longitude
                            if self.GPSTracks[j][i].longitudeEW == 'W': 
                                longitude = -longitude
                            theFeature.setGeometry(QgsGeometry.fromPoint(QgsPoint(longitude,latitude)))
                            theFeature.setAttributes([0, latitude])
                            theFeature.setAttributes([1, longitude])
                            theFeature.setAttributes([2, self.GPSTracks[j][i].numSatellites])
                            theFeature.setAttributes([3, self.GPSTracks[j][i].hdop])
                            theFeature.setAttributes([4, self.GPSTracks[j][i].theDateTime])
                            theFeature.setAttributes([5, self.GPSTracks[j][i].fixQuality])
                            theFeature.setAttributes([6, self.GPSTracks[j][i].bearing])
                            theFeature.setAttributes([7, self.GPSTracks[j][i].speed])
                            theFeature.setAttributes([8, j+1])
                            pointsFile.addFeature(theFeature)
                            
                    del pointsFile # del file object to force a flush and close
                    
            if len(myShapeFileNamesDlg.lneLinesFileName.text()) > 0:
                # set up the fields for the Lines SHAPE file
                lines_box = QgsFields()
                lines_box.append(QgsField("SDATETIME", QVariant.String, "String", 19, 0))
                lines_box.append(QgsField("EDATETIME", QVariant.String, "String", 19, 0))
                lines_box.append(QgsField("TRACKNUM", QVariant.Int, "Integer", 2, 0))
                
                linesFile, fileOK = self.createSHAPEfile(myShapeFileNamesDlg.lneLinesFileName.text(),lines_box,QGis.WKBLineString,CRS)
                if fileOK:
                    for j in range(len(self.GPSTracks)):
                        theFeature = QgsFeature()
                        pointsList = []
                        for i in range(len(self.GPSTracks[j])):
                            latitude = self.GPSTracks[j][i].latitude
                            if self.GPSTracks[j][i].latitudeNS == 'S': 
                                latitude = -latitude
                            longitude = self.GPSTracks[j][i].longitude
                            if self.GPSTracks[j][i].longitudeEW == 'W': 
                                longitude = -longitude
                            pointsList.append(QgsPoint(longitude,latitude))
                            
                        theFeature.setGeometry(QgsGeometry.fromPolyline(pointsList))
                        theFeature.setAttributes([0, self.GPSTracks[j][0].theDateTime])
                        theFeature.setAttributes([1, self.GPSTracks[j][len(self.GPSTracks[j])-1].theDateTime])
                        theFeature.setAttributes([2, j+1])
                        linesFile.addFeature(theFeature)
                        
                    del linesFile # del file object to force a flush and close
                    

    def createSHAPEfile(self,fileName, fileFields, fileType, crs):
        '''
        this function creates a new, empty shape file for use in writing points or lines
        Returns: SHAPEfile, status
            if status == True then SHAPEfile is OK to use, if False then an error occured and cannot use SHAPEFile
            
        Input Parameters:
            fileName = full name of the SHAPE file to be created
            fileFields = map of QgsFields to use for the attributes of the SHAPE file
            fileType = QGis.WKBPoint for points file <or> QGis.WKBLine for lines file
            crs = the QgsCoordinateReferenceSystem to use for the file
        '''
        
        status = True # default is no error
        SHAPEfile = QgsVectorFileWriter(fileName,"CP1250",fileFields,fileType,crs)
        typeName = 'Points' if fileType == QGis.WKBPoint else 'Lines'
        if SHAPEfile.hasError() != QgsVectorFileWriter.NoError:
            status = False # report an error
            if SHAPEfile.hasError() == QgsVectorFileWriter.ErrDriverNotFound:
                QMessageBox.warning(self.iface.mainWindow(),"trackGPS - makeShapeFiles","Error creating " + typeName + " SHAPE file" +\
                                            " ERROR=\'ErrDriverNotFound\' - saving " + typeName + " is aborted")
            elif SHAPEfile.hasError() == QgsVectorFileWriter.ErrCreateDataSource:
                QMessageBox.warning(self.iface.mainWindow(),"trackGPS - makeShapeFiles","Error creating " + typeName + " SHAPE file" +\
                                            " ERROR=\'ErrCreateDataSource\' - saving " + typeName + " is aborted")
            elif SHAPEfile.hasError() == QgsVectorFileWriter.ErrCreateLayer:
                QMessageBox.warning(self.iface.mainWindow(),"trackGPS - makeShapeFiles","Error creating " + typeName + " SHAPE file" +\
                                            " ERROR=\'ErrCreateLayer\' - saving " + typeName + " is aborted")
            elif SHAPEfile.hasError() == QgsVectorFileWriter.ErrAttributeTypeUnsupported:
                QMessageBox.warning(self.iface.mainWindow(),"trackGPS - makeShapeFiles","Error creating " + typeName + " SHAPE file" +\
                                            " ERROR=\'ErrAttributeTypeUnsupported\' - saving " + typeName + " is aborted")
            else:
                QMessageBox.warning(self.iface.mainWindow(),"trackGPS - makeShapeFiles","Error creating " + typeName + " SHAPE file" +\
                                            " ERROR=\'UNKOWN ERROR\' saving " + typeName + " is aborted")
        return SHAPEfile,status
        
        
    #Metodo per l'acquisizione tramite soglia di distanza
    def tresholdAcquisition(self, aGPSPosition):
    
        #Costanti per il calcolo della distanza
        R_Terra = 6372.795477598
        acquisito = False
        
        
        #Acquisisco la soglia di distanza, da input e la converto in float
        soglia = self.dock.lineTreshold.text()
        if not soglia.isnumeric():
            self.read.stop()
            self.positionMarker.hide()
            self.dock.btnStart.setText("Start")
            self.dock.gpsInformation.setText("Gets GPS Receiver Information")
            QMessageBox.warning(self.iface.mainWindow(),"ATENZIONE","Inserire solo valori numerici nella soglia di distanza.")
        else:
            soglia = float(soglia)
            soglia = soglia / 1000
    
        #Conversione dei gradi in radianti
        lat_alfa = math.radians(aGPSPosition.latitude)
        lat_beta = math.radians(self.GPSPositions[-1].latitude)
        lon_alfa = math.radians(aGPSPosition.longitude)
        lon_beta = math.radians(self.GPSPositions[-1].longitude)
        
        #Calcolo la differenza di lat e lon
        dLat = lat_alfa - lat_beta
        dLon = lon_alfa - lon_beta
            
         
        a = math.sin(dLat/2)*math.sin(dLat/2)+math.sin(dLon/2)*math.sin(dLon/2)* math.cos(lat_alfa) * math.cos(lat_beta)
            
        #Calcolo il terzo lato del triangolo sferico
        c = 2*math.atan2(math.sqrt(a),math.sqrt(1-a))
           
        distanza = c * R_Terra
           
        #Controllo con la soglia di distanza e eventualmente acquisisco
        if distanza > soglia:
            acquisito = True    
                    
        return acquisito
        
    
    #Metodo timeIntervals() per il controllo della soglia temporale
    def timeIntervals(self, aGPSPosition):
    
        #Variabile booleana di ritorno
        acquisito = False
        
        #Stringa per il formato della data 
        formato = '%Y-%m-%d %H:%M:%S'
        
        #Metto le due date, quella dell'ultima acquisizione e quella da valutare in due stringhe
        dataA = aGPSPosition.theDateTime
        dataB = self.GPSPositions[-1].theDateTime
        
        #Tramite il metodo time.strptime() realizziamo due strutte tempo per le due date
        struct_A = time.strptime(dataA,formato)
        struct_B = time.strptime(dataB,formato)
        
        #Otteniamo i valori di confronto
        confrontoA = datetime.datetime.fromtimestamp(time.mktime(struct_A))
        confrontoB = datetime.datetime.fromtimestamp(time.mktime(struct_B))
        
        #Otteniamo la differenza
        differenza = (confrontoA - confrontoB).seconds
        
        #Acquisisco la soglia di distanza temporale e gestisco eventualmente l'inserimento di valori non numerici
        intervalli = self.dock.lineTimeIntervals.text()
        if not intervalli.isnumeric():
            self.read.stop()
            self.positionMarker.hide()
            self.dock.btnStart.setText("Start")
            self.dock.gpsInformation.setText("Gets GPS Receiver Information")
            QMessageBox.warning(self.iface.mainWindow(),"ATENZIONE","Inserire solo valori numerici nella soglia temporale.")
        else:
            intervalli = float(intervalli)
        
        #Controllo se la differenza e maggiore della soglia
        if differenza > intervalli:
          acquisito = True
          
        return acquisito 
