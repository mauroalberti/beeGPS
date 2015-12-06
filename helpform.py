#!/usr/bin/env python
###############################################################################
#
# Project:  QGIS Image Cutter Python Plugin
# Purpose:  To extract image tiles from a QGIS Image Layer.
# Author:   Bob Bruce, P.Eng., Bob.Bruce@pobox.com (www.hwps.ca)
# Date:     2009-09-17
#
###############################################################################
# 
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.
# 
# You should have received a copy of the GNU Library General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
###############################################################################

from PyQt4.QtCore import *
from PyQt4.QtGui import *
import qrc_resources


class HelpForm(QDialog):

    def __init__(self, page, parent=None):
        super(HelpForm, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setAttribute(Qt.WA_GroupLeader)

        self.pageLabel = QLabel()

        self.textBrowser = QTextBrowser()

        layout = QVBoxLayout()
        layout.addWidget(self.textBrowser)
        self.setLayout(layout)

        self.connect(self.textBrowser, SIGNAL("sourceChanged(QUrl)"),
                     self.updatePageTitle)

        self.textBrowser.setSearchPaths([":/"])
        self.textBrowser.setSource(QUrl(page))
        self.resize(960, 800)
        application_name = QApplication.applicationName()
        self.setWindowTitle(("%s Help") % application_name)


    def updatePageTitle(self):
        self.pageLabel.setText(self.textBrowser.documentTitle())


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    form = HelpForm("TheQGISGPSTrackerPlugin.html")
    form.show()
    app.exec_()

