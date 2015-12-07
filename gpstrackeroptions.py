
import os
import sys
import math


from PyQt4.QtCore import * 
from PyQt4.QtGui import *
from PyQt4 import uic


from functools import partial


globalpath = os.path.dirname(os.path.abspath(__file__))
gpsTrackingOptionsDlg, base_class = uic.loadUiType(os.path.join(globalpath,"gpsTrackerOptions.ui"))



class GPSTrackerOptions(QDialog, gpsTrackingOptionsDlg):
    """
    Class to set up the dialog for all of the tracker options. Parameter trackerObject is used to pass the current options
    """
        
            
    def __init__(self, trackerObject, parent=None):
        
        super(GPSTrackerOptions, self).__init__(parent)

        self.port_minval = 10       
        self.port_maxval = 18
        
        self.setupUi(self)

        self.trackerObject = trackerObject # save this for use in the methods

        # Load the port speeds selection box
        for i in range(len(self.trackerObject.read.session.baudRates)):
            self.cbxPortSpeed.addItem(str(self.trackerObject.read.session.baudRates[i]), i)

        # Load the ports selection box
        for i in range(self.port_minval, self.port_maxval+1):
            pName = 'COM' + str(i)
            self.cbxPortName.addItem(pName, i)
            
        # Set the port ID and speeds according to the defaults or recovered values
        if self.trackerObject.searchAllConnectionsSpeeds:
            self.rbtTryAll.setChecked(True)
            self.cbxPortName.setDisabled(True)
            self.cbxPortSpeed.setDisabled(True)
        else:
            self.rbtSetConnection.setChecked(True)
            self.cbxPortName.setDisabled(False)
            self.cbxPortSpeed.setDisabled(False)
            self.cbxPortName.setCurrentIndex(self.trackerObject.serialPortNumber)
            self.cbxPortSpeed.setCurrentIndex(self.trackerObject.serialPortSpeed)
        
        
        # Set Initial GPS Display Options
        
        # Marker Fill color
        pal = self.btnMarkerFillColor.palette()
        pal.setColor(QPalette.Active, QPalette.Button, self.trackerObject.markerFillColor)
        pal.setColor(QPalette.Active, QPalette.Window, self.trackerObject.markerFillColor)
        self.btnMarkerFillColor.setPalette(pal)
        self.markerFillColor = self.trackerObject.markerFillColor
        
        # Marker Outline color
        pal = self.btnMarkerOutlineColor.palette()
        pal.setColor(QPalette.Active, QPalette.Button, self.trackerObject.markerOutlineColor)
        pal.setColor(QPalette.Active, QPalette.Window, self.trackerObject.markerOutlineColor)
        self.btnMarkerOutlineColor.setPalette(pal)
        self.markerOutlineColor = self.trackerObject.markerOutlineColor
        
        # GPS Track Line color 
        pal = self.btnTrackLineColor.palette()
        pal.setColor(QPalette.Active, QPalette.Button, self.trackerObject.lineColor)
        pal.setColor(QPalette.Active, QPalette.Window, self.trackerObject.lineColor)
        self.btnTrackLineColor.setPalette(pal)
        self.lineColor = self.trackerObject.lineColor
        
        # GPS Track Line Width
        self.sbxTrackWidth.setValue(self.trackerObject.trackLineWidth)
        self.cbxSaveGPSTrack.setChecked(self.trackerObject.saveInSHAPEFile)

        # load the combo box for the marker type
        self.cbxMarkerType.setIconSize(QSize(29,29))
        self.cbxMarkerType.setMaxCount(5)
        self.cbxMarkerType.addItem(QIcon(os.path.join(globalpath,"images\\triangle.png")),"Notched Triangle", 0)
        self.cbxMarkerType.addItem(QIcon(os.path.join(globalpath,"images\\wideArrow.png")),"Wide Arrow", 1)
        self.cbxMarkerType.addItem(QIcon(os.path.join(globalpath,"images\\bluntArrow.png")),"Blunt Arrow", 2)
        self.cbxMarkerType.addItem(QIcon(os.path.join(globalpath,"images\\pointedStick.png")),"Pointed Stick", 3)

        # Marker Selection
        self.markerNum = self.trackerObject.markerNumber
        self.cbxMarkerType.setCurrentIndex(self.markerNum)

        # Connect the actions to its methods
        QObject.connect(self.btnTrackLineColor, SIGNAL("clicked()"), self.colorClicked)
        QObject.connect(self.btnMarkerFillColor, SIGNAL("clicked()"), self.colorClicked)
        QObject.connect(self.btnMarkerOutlineColor, SIGNAL("clicked()"), self.colorClicked)
        QObject.connect(self.rbtTryAll, SIGNAL("clicked()"), self.setConnectionSettings)
        QObject.connect(self.rbtSetConnection, SIGNAL("clicked()"), self.setConnectionSettings)
        QObject.connect(self.cbxPortSpeed, SIGNAL("currentIndexChanged(int)"), self.getComboBoxChange)


    def colorClicked(self):
        btnColor = self.sender().palette().color(QPalette.Active, QPalette.Window)
        newColor = QColorDialog.getColor(btnColor)
        if btnColor != newColor:
            pal = self.sender().palette()
            pal.setColor(QPalette.Active, QPalette.Button, newColor)
            pal.setColor(QPalette.Active, QPalette.Window, newColor)
            self.sender().setPalette(pal)
            self.sender().colorChanged = True
            # the following class variables are created/set for easier access to the button's colors
            if self.sender() == self.btnTrackLineColor:
                self.lineColor = newColor
            elif self.sender() == self.btnMarkerFillColor:
                self.markerFillColor = newColor
            elif self.sender() == self.btnMarkerOutlineColor:
                self.markerOutlineColor = newColor


    def setConnectionSettings(self):
        """The Connection Selection has changed, detect it and if the user is selecting a particular
           connection set, enable the controls"""
           
        if self.rbtTryAll.isChecked(): # user has elected to search all connections and speeds
            self.trackerObject.searchAllConnectionsSpeeds = True
            self.cbxPortName.setDisabled(True)
            self.cbxPortSpeed.setDisabled(True)
        else: # a particular connection is being selected
            self.trackerObject.searchAllConnectionsSpeeds = False
            self.cbxPortName.setDisabled(False)
            self.cbxPortSpeed.setDisabled(False)
            self.cbxPortName.setCurrentIndex(self.trackerObject.serialPortNumber)
            self.cbxPortSpeed.setCurrentIndex(self.trackerObject.serialPortSpeed)


    def getComboBoxChange(self,theIndex):
        
        if self.sender() == self.cbxPortSpeed:
            self.trackerObject.serialPortSpeed = theIndex
        else:
            self.trackerObject.serialPortNumber = theIndex
            
            
