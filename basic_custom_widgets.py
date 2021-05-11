from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *


# set up parent.
def setUpParent(parent):
    if parent is None:
        return (None, None, None)
    else:
        return (parent, parent.log, parent.status)


# logging
def _dbg(obj, string):
    if obj is not None:
        if obj.log is not None:
            obj.log.debug(string)

def _info(obj, string):
    if obj is not None:
        if obj.status is not None:
            obj.status.info(string)

def _err(obj, string):
    if obj is not None:
        if obj.status is not None:
            obj.status.err(string)

def _defaultSlot(slot_type=None, name=None):
    string = "{slot_type} is not defined for widget - {name}".format(slot_type=slot_type, name=name)
    _err(None, string)



##################################
#
# LineEdit + One Button To Submit.
#
###################################


#
# user supplies slot function. 
# slot gets access to self, and self.parent.
# 
class Input(QWidget):
    def __init__(self, btn_name="add", buttonClickedSlot=None, parent=None, name=None):
        super(Input, self).__init__()
        (self.parent, self.log, self.status) = setUpParent(parent)
        self.name = name

        self.qle = QLineEdit()
        self.btn = QPushButton(btn_name)
        self.buttonClickedSlot = buttonClickedSlot
        
        # call setting up UI
        self.setUI()
    
    def setUI(self):
        hbox = QHBoxLayout()
        hbox.addWidget(self.qle, 85)
        hbox.addWidget(self.btn, 15)
        self.setLayout(hbox)
        self.btn.clicked.connect(self.buttonClicked)
        
    def getInput(self):
        return self.qle.text().strip()

    def getContainer(self):
        return self

    @pyqtSlot()
    def buttonClicked(self):
        if self.buttonClickedSlot is None:
            _defaultSlot("buttonClicked", self.name)
        else:
            self.buttonClickedSlot()  

    


########################################################
#
#
# Logs open in a Dialog and status is shown at the end.
#
#
########################################################

import sys, logging

# Uncomment below for terminal log messages
# logging.basicConfig(level=logging.DEBUG, format=' %(asctime)s - %(name)s - %(levelname)s - %(message)s')

class QTextEditLogger(logging.Handler):
    def __init__(self, parent):
        super().__init__()
        self.widget = QPlainTextEdit(parent)
        self.widget.setReadOnly(True)

    def emit(self, record):
        msg = self.format(record)
        self.widget.appendPlainText(msg)


class LoggingDialog(QDialog, QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

        logTextBox = QTextEditLogger(self)
        # You can format what is printed to text box
        logTextBox.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(logTextBox)
        # You can control the logging level
        logging.getLogger().setLevel(logging.DEBUG)

        self._button =QPushButton(self)
        self._button.setText('Test Me')

        layout = QVBoxLayout()
        # Add the new logging box widget to the layout
        layout.addWidget(logTextBox.widget)
        layout.addWidget(self._button)
        self.setLayout(layout)

        # Connect signal to slot
        self._button.clicked.connect(self.test)

    def debug(self, string):
        logging.debug (string)

    def info(self, string):
        logging.info(string)

    def warn(self, string):
        logging.info(string)

    def err(self, string):
        logging.error(string)


    def test(self):
        logging.debug('damn, a bug')
        logging.info('something to remember')
        logging.warning('that\'s not right')
        logging.error('foobar')

#
# widget to show the Status:
class LoggingStatus(QWidget):
    def __init__(self, parent=None):
        super(LoggingStatus, self).__init__()
        self.parent = parent
        if parent is not None:
            self.log = parent.log
        self.label = QLabel()
        self.button = QPushButton("Logs")
        self.button.clicked.connect(self.showLog)

        # ui
        self.setUI()

    def setUI(self):
        hbox = QHBoxLayout()
        hbox.addWidget(self.label, 90)
        hbox.addWidget(self.button, 10)
        self.setLayout(hbox)
    
    def info(self, string):
        if self.log:
            self.log.info(string)
        self.label.setText(string)
        self.label.setStyleSheet("QLabel {color: green;};")

    def err(self, string):
        if self.log:
            self.log.err(string)
        self.label.setText(string)
        self.label.setStyleSheet("QLabel {color: red;};")

    @pyqtSlot()
    def showLog(self):
        self.log.show()




#########################################################
#
#
# Sortable Table, filling directly from DataFrames
#
#
##########################################################
import pandas as pd
from natsort import natsorted, index_natsorted, order_by_index
# show dataframe as QTableView
# https://stackoverflow.com/questions/55310051/displaying-pandas-dataframe-in-qml/55310236#55310236
# https://github.com/eyllanesc/stackoverflow/tree/master/questions/44603119
#
# usage => Qtableview.setModel(DFModel(df)), QTableView.setSorting(enabled)
# #
class DataFrameModel(QAbstractTableModel):
    DtypeRole = Qt.UserRole + 1000
    ValueRole = Qt.UserRole + 1001

    def __init__(self, df=pd.DataFrame(), parent=None):
        super(DataFrameModel, self).__init__(parent)
        self._dataframe = df

    def setDataFrame(self, dataframe):
        self.beginResetModel()
        self._dataframe = dataframe.copy()
        self.endResetModel()

    def dataFrame(self):
        return self._dataframe

    dataFrame = pyqtProperty(pd.DataFrame, fget=dataFrame, fset=setDataFrame)

    pyqtSlot(int, Qt.Orientation, result=str)
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self._dataframe.columns[section]
            else:
                return str(self._dataframe.index[section])
        return QVariant()

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._dataframe.index)

    def columnCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return self._dataframe.columns.size

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < self.rowCount() \
            and 0 <= index.column() < self.columnCount()):
            return QVariant()
        row = self._dataframe.index[index.row()]
        col = self._dataframe.columns[index.column()]
        dt = self._dataframe[col].dtype

        val = self._dataframe.iloc[row][col]
        if role == Qt.DisplayRole:
            return str(val)
        elif role == DataFrameModel.ValueRole:
            return val
        if role == DataFrameModel.DtypeRole:
            return dt
        return QVariant()

    def roleNames(self):
        roles = {
            Qt.DisplayRole: b'display',
            DataFrameModel.DtypeRole: b'dtype',
            DataFrameModel.ValueRole: b'value'
        }
        return roles
    
    def sort(self, column, order):
        self.layoutAboutToBeChanged.emit()
        if order == 0:
            self._dataframe = self._dataframe.reindex(index=order_by_index(self._dataframe.index, index_natsorted(eval('self._dataframe.%s' % (list(self._dataframe.columns)[column])))))
        else:
            self._dataframe = self._dataframe.reindex(index=order_by_index(self._dataframe.index, reversed(index_natsorted(eval('self._dataframe.%s' % (list(self._dataframe.columns)[column]))))))

        self._dataframe.reset_index(inplace=True, drop=True)
        self.setDataFrame(self._dataframe)
        self.layoutChanged.emit()

    # def sort(self, Ncol, order):
    #     """Sort table by given column number."""
    #     self.layoutAboutToBeChanged.emit()
    #     self._dataframe = self._dataframe.sort_values(self.headers[Ncol],
    #                                   ascending=order == Qt.AscendingOrder)
    #     self.layoutChanged.emit()


class DfTable(QTableView):
    def __init__(self, parent=None, name=None, cellDoubleClickSlot=None):
        super(DfTable, self).__init__()
        (self.parent, self.log, self.status) = setUpParent(parent)
        self.name = name
        self.cellDoubleClickSlot = cellDoubleClickSlot

        # 
        self.setSortingEnabled(True)
        self.doubleClicked.connect(lambda qmodelindex: self.cellDoubleClick(qmodelindex))

    def cellDoubleClick(self, qmodelindex):
        #https://stackoverflow.com/questions/19442050/qtableview-how-can-i-get-the-data-when-user-click-on-a-particular-cell-using-mo
        _dbg(self, "double clicked -- " + str(qmodelindex.data()))
        if self.cellDoubleClickSlot is not None:
            self.cellDoubleClickSlot(qmodelindex)
        else:
            _defaultSlot("cellDoubleClickSlot", str(self.name))


    def setDf(self, df):
        self.setModel(DataFrameModel(df))

    def getContainer(self):
        return self


################################################
#
# Tab Container : tab updates only when active.
#
###############################################
class TabContainer(QTabWidget):
    def __init__(self, tab_list=[], parent=None, close_button=False, name=None):
        super(TabContainer, self).__init__()
        (self.parent, self.log, self.status) = setUpParent(parent)
        self.name = name
        
        # ui
        self.tab_list = tab_list    # list of tabs
        self.setUI()
        self.currentChanged.connect(self.tabChanged)

        # closable
        if close_button:
            self.setTabsClosable(True)
            self.tabCloseRequested.connect(lambda index: self.closeTab(index))
            #self.tabCloseRequested.connect(self.closeTab)

    def getContainer(self):
        return self

    @pyqtSlot()
    def closeTab(self, index):
        _dbg(self, "closing tab @ "+ str(index) +": widget = " + str(self.name))
        self.removeTab(index)
        self.tab_list.pop(index)


    def addTabList(self, tab_list):
        self.tab_list = tab_list
        self.setUI()

    # 
    # add one tab dict
    def addTabDict(self, tab):
        self.tab_list.append(tab)
        self.addTab(tab["widget"], tab["name"])
        tab["visible"] = True
        _dbg(self, "added tab. tab_list: " + str(self.tab_list) + "\nwidget = " + str(self.name))


    def setUI(self):
        for tab in self.tab_list:
            if tab["visible"] == False:
                self.addTab(tab["widget"], tab["name"])
                tab["visible"] = True

        if self.status:
            self.status.info("added tabs to TabWidget")


    def resetUpdateStatus(self):            # reset status if the tab needs to repaint
        for tab in self.tab_list:
            tab["update_status"] = False
        _dbg("resetting update status in widget == " + str(self.name))

    def isPendingUpdate(self):              # check whether it is required to update the tab.
        curr_index = self.currentIndex()
        return not self.tab_list[curr_index]["update_status"]

    def hasSlot(self):
        curr_index = self.currentIndex()
        if "slot" not in self.tab_list[curr_index].keys():
            return None
        return self.tab_list[curr_index]["slot"]

    @pyqtSlot()
    def tabChanged(self):
        if self.isPendingUpdate():
            slot = self.hasSlot()
            if slot is not None:
                slot()
            else:
                _defaultSlot("tabChanged", str(self.name))

    @classmethod
    def createTabDict(self, name, widget, slot):
        """ name: appears on tab.
            widget: child of tab, that will appear.
            slot: function executed everytime the tab is visited."""
        d = {}
        d["name"] = name
        d["widget"] = widget
        d["slot"] = slot
        d["visible"] = False
        d["update_status"] = False
        return d



###############################
#
# List
#
###############################

class List(QListWidget):
    def __init__(self, parent=None, itemClickedSlot=None, name=None):
        super(List, self).__init__()
        (self.parent, self.log, self.status) = setUpParent(parent)
        self.name = name
        self.itemClickedSlot = itemClickedSlot
        self.itemClicked.connect(self.itemClick)

    def defaultSlot(self):
        if self.status is not None:
            self.status.err("There is no slot for List")

    def getContainer(self):
        return self

    @pyqtSlot()
    def itemClick(self):
        if self.slot is not None:
            self.itemClickedSlot()
        else:
            _defaultSlot("itemClicked", str(self.NoFrame) )


########################3
#
# Downloader
#
#########################
import time

# Thread
# user provides a function to run in a thread.
# function should take every data from parent. 
#
class Downloader(QThread):
    downloaded = pyqtSignal()
    def __init__(self, parent=None, threadRun=None):
        super(Downloader, self).__init__()
        (self.parent, self.log, self.status) = setUpParent(parent)
        self.threadRun = threadRun
        if self.parent:
            self.update_interval = self.parent.update_interval
        else:
            self.update_interval = 30

    def getContainer(self):
        return self
    
    def run(self):
        while True:
            if self.threadRun is None:
                _err(self, "No function for this downloader.")
            else:
                _info(self, "Downloader starting ... ")
                self.threadRun()         # each user defined function will take 
            self.downloaded.emit()
            _info(self, "Download completed.")
            time.sleep(self.parent.update_interval)




##############################3
#
# QMessageBox
#
##############################