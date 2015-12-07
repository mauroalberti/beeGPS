
from math import *

from PyQt4 import QtCore, QtGui

from qgis.core import *
from qgis.gui import *



class RoutePointMarker(QgsMapCanvasItem):
    
    """ marker for start and end of the route """
   
    Start, Stop = range(2)
   
   
    def __init__(self, canvas, markerType):
        
        QgsMapCanvasItem.__init__(self, canvas)
        self.d = 21
        self.pos = None   
        self.markerType = markerType
        self.setZValue(90)
     
      
    def setPosition(self, pos):
        
        if pos:
            self.pos = QgsPoint(pos)
            self.setPos(self.toCanvasCoordinates(self.pos))
            self.show()
            #self.update()
        else:
            self.hide()


    def boundingRect(self):
        
        return QtCore.QRectF(-1,-21, 12, 22)


    def paint(self, p, xxx, xxx2):

        QP = QtCore.QPoint
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.drawLine(QP(0,0), QP(0,-10))
        
        if self.markerType == RoutePointMarker.Start:
            p.setBrush(QtGui.QBrush(QtGui.QColor(0,255,0)))
        else:
            p.setBrush(QtGui.QBrush(QtGui.QColor(255,0,0)))
        
        poly = QtGui.QPolygon(3)
        poly[0] = QP(0,-10)
        poly[1] = QP(0,-20)
        poly[2] = QP(10,-15)
        p.drawPolygon(poly)


    def updatePosition(self):
        
        self.setPosition(self.pos)



class PositionMarker(QgsMapCanvasItem):
    """ marker for current GPS position """
    
    def __init__(self, canvas, markerNumber=0, fillColor=QtGui.QColor(0,0,0), outlineColor=QtGui.QColor(255,255,0)):

        QgsMapCanvasItem.__init__(self, canvas)
        self.pos = None
        self.hasPosition = False
        self.d = 20
        self.angle = 0
        self.fillColor = fillColor
        self.markerNumber = markerNumber
        self.outlineColor = outlineColor
        self.setZValue(100) # must be on top


    def newCoords(self, pos, cap=0):
        
        #~ print pos
        if self.pos != pos:
            save = self.pos
            self.pos = QgsPoint(pos) # copy
            if save and cap == 0:
                # compute angle from positions
                # this is a small distance, simply use pythagore
                if (pos.x()-save.x()) == 0:
                    self.angle = 90
                else:
                    self.angle = 90 - degrees(atan((pos.y()-save.y()) / (pos.x()-save.x()) ))
                if (save.x() > pos.x()): # go west !
                    self.angle = 360 - self.angle
                #print self.angle
            else:
                self.angle = cap
                
            self.updatePosition()


    def setHasPosition(self, has):
        
        if self.hasPosition != has:
            self.hasPosition = has
            self.update()


    def updatePosition(self):
        
        if self.pos:
            self.setPos(self.toCanvasCoordinates(self.pos))
            self.update()


    def paint(self, p, xxx, xxx2):
        
        if not self.pos:
            return
        
        path = QtGui.QPainterPath()
     
        if self.markerNumber == 0:
            # draw notched triangle
            path.moveTo(0,-10)
            path.lineTo(10,10)
            path.lineTo(0,5)
            path.lineTo(-10,10)
            path.lineTo(0,-10)
        elif self.markerNumber == 1:
            # draw wide arrow
            path.moveTo(0,0)
            path.lineTo(-10,-5)
            path.lineTo(-7,-8)
            path.lineTo(-2,-6)
            path.lineTo(-2,-15)
            path.lineTo(2,-15)
            path.lineTo(2,-6)
            path.lineTo(7,-8)
            path.lineTo(10,-5)
            path.lineTo(0,0)
        elif self.markerNumber == 2:
            # draw short, blunt arrow
            path.moveTo(0,0)
            path.lineTo(-10,-5)
            path.lineTo(-7,-8)
            path.lineTo(-4,-7)
            path.lineTo(-4,-15)
            path.lineTo(4,-15)
            path.lineTo(4,-7)
            path.lineTo(7,-8)
            path.lineTo(10,-5)
            path.lineTo(0,0)
        elif self.markerNumber == 3:
            # long stick with a point on it
            path.moveTo(0,0)
            path.lineTo(-8,-8)
            path.lineTo(-8,-24)
            path.lineTo(8,-24)
            path.lineTo(8,-8)
            path.lineTo(0,0)
     
        # render position with angle
        p.save()
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        if self.hasPosition:
            p.setBrush(QtGui.QBrush(self.fillColor))
        else:
            p.setBrush(QtGui.QBrush(QtGui.QColor(200,200,200)))
        p.setPen(self.outlineColor)
        p.rotate(self.angle)
        p.drawPath(path)
        p.restore()


    def boundingRect(self):
        
        return QtCore.QRectF(-self.d,-self.d, self.d*2, self.d*2)
    
    
