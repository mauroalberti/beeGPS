
import os, sys, math


from PyQt4.QtCore import * 
from PyQt4.QtGui import *
from PyQt4 import uic


from functools import partial


globalpath = os.path.dirname(os.path.abspath(__file__))
shapeFileNamesDlg, base_class = uic.loadUiType(os.path.join(globalpath,"saveShapeFile.ui"))


class ShapeFileNames(QDialog, shapeFileNamesDlg):
    
    def __init__(self, startDirectory, parent=None):
        """
        Class to set up the dialog for getting the names of the output SHAPE file(s).
        Parameter startDirectory is used to pass the name of the folder containing
        the project file in case the user wants to put the SHAPE files there.
        """
                
        super(ShapeFileNames, self).__init__(parent)
        self.setupUi(self)

        self.startDirectory = startDirectory
        
        # Set up the messages for the two check boxes
        QObject.connect(self.chkSavePoints, SIGNAL("stateChanged(int)"), self.manageCheckBoxes)
        QObject.connect(self.chkSaveLines, SIGNAL("stateChanged(int)"), self.manageCheckBoxes)
        QObject.connect(self.btnGetPointFilename, SIGNAL("clicked()"), self.getShapeFileName)
        QObject.connect(self.btnGetLineFilename, SIGNAL("clicked()"), self.getShapeFileName)
        
        
    def manageCheckBoxes(self, CheckState):
        """
        Sets the controls for each file type (either Points of Lines) enabled or disabled according
        to the value of the checkbox
        """
        
        enableThem = False
        if CheckState == 2: enableThem = True
        if self.sender().objectName() == 'chkSavePoints': # want to save points file, enable widgets
            self.btnGetPointFilename.setEnabled(enableThem)
            self.lnePointsFileName.setEnabled(enableThem)
        elif self.sender().objectName() == 'chkSaveLines': # want to save lines file, enable widgets
            self.btnGetLineFilename.setEnabled(enableThem)
            self.lneLinesFileName.setEnabled(enableThem)
        else:
            return
    
    
    def getShapeFileName(self):

        if self.sender().objectName() == 'btnGetPointFilename':
            theType = 'Points'
        elif self.sender().objectName() == 'btnGetLineFilename':
            theType = 'Lines'
        message = "Select a file name for the output " + theType + " SHAPE file"
        directory = self.startDirectory + '\\' + theType + '.shp'
        fileName = QFileDialog.getSaveFileName(self, message, directory,\
                                "Shape File (*.shp)")
        if fileName:
            if self.sender().objectName() == 'btnGetPointFilename':
                self.lnePointsFileName.insert(fileName)
            elif self.sender().objectName() == 'btnGetLineFilename':
                self.lneLinesFileName.insert(fileName)

    
