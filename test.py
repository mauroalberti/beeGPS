import os

globalpath = os.path.dirname(os.path.abspath(__file__))
print 'globalpath =',globalpath
iconPathName = os.path.join(globalpath,"images\\triangle.png")
print 'iconPathName =',iconPathName
print 'other path=',os.path.join(globalpath,"gpsTrackerOptions.ui")