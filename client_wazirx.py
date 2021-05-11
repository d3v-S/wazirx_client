import sys, requests, json, collections, time

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

import pandas as pd, json, pickle
from functools import partial
from os import path

from basic_custom_widgets import *
from client_utils import *
from widget_candlestick_charts import *

import yfinance

##########
#  WAZIRX
##########


#
#  Main Window.
# 
class WazirxClient(QWidget):
    def __init__(self, parent=None):
        super(WazirxClient, self).__init__()
        self.parent = parent
        if self.parent is not None:
            self.log = self.parent.log
            self.status = self.parent.status
        else:
            self.log = LoggingDialog()
            self.status = LoggingStatus(self)

        # config
        self.update_interval = 60

        # serialized data
        self.fav_pkl = "wazirx_fav.pkl"
        self.alerts_pkl = "wazirx_alerts.pkl"
      
        # data
        self.favourites = set()
        self.fav_df = None
        self.market_df = None
        self.clicked_crypto = None

        # alert
        self.alerts = WazirxAlerts(self)
    

        # load from disk
        self.loadFromDisk()


        # ui setup
            # input
            # tab
            # status
        self.input = Input(parent=self, buttonClickedSlot=self.inputSlot_AddToFavourites)
        self.tab_container = TabContainer(  parent=self, 
                                            tab_list=[  self.firstTab(),
                                                        self.secondTab(),
                                                        self.thirdTab()
                                                ])
        self.setUI()
        
        # thread
        self.thread = Downloader(self, threadRun=self.thread_run)
        self.thread.downloaded.connect(self.updateUI)
        self.thread.start()

    def setUI(self):
        vbox = QVBoxLayout()
        vbox.addWidget(self.input, 10)
        vbox.addWidget(self.tab_container, 85)
        vbox.addWidget(self.status, 5)
        self.setLayout(vbox)

    def loadFromDisk(self):
        if path.exists(self.fav_pkl):
            self.favourites = ClientUtils.fileToObj(self.fav_pkl)
        
        if path.exists(self.alerts_pkl):
            self.alerts = ClientUtils.fileToObj(self.alerts_pkl)

    def saveFavToDisk(self):
        ClientUtils.objToFile(self.favourites, self.fav_pkl)

    def saveAlertsToDisk(self):
        pass





    #
    # Tab List:
    def tabChangedSlot_Fav(self):
        if self.fav_df is not None:
            self.tab_container.currentWidget().setDf(self.fav_df)

    def tabChangedSlot_Market(self):
        if self.market_df is not None:
            self.tab_container.currentWidget().setDf(self.market_df)

    # update all alerts:
    def tabChangedSlot_Alerts(self):
        self.tab_container.currentWidget().clear()
        for item in self.alerts.rule_list:
            self.tab_container.currentWidget().addItem(str(item["rule_tuple"]))



    def firstTab(self):
        d = TabContainer.createTabDict( name = "Favourites", 
                                        widget = DfTable(self, cellDoubleClickSlot=self.cellDoubleClicked),
                                        slot = self.tabChangedSlot_Fav)
        return d

    def secondTab(self): 
        d = TabContainer.createTabDict( name = "Market", 
                                        widget = DfTable(self, cellDoubleClickSlot=self.cellDoubleClicked),
                                        slot = self.tabChangedSlot_Market)
        return d
    

    # show alerts in 3rd one.
    def thirdTab(self):
        d = TabContainer.createTabDict( name = "Alerts", 
                                        widget = List(parent=self, itemClickedSlot=self.listItemClickedSlot),
                                        slot = self.tabChangedSlot_Alerts)
        return d


    # input slot
    # calling container is the customwidget.
    def inputSlot_AddToFavourites(self, calling_container=None):
        text = self.input.getInput()
        if text[0] == "$":
            self.alerts.addAlert(text)   
            self.saveAlertsToDisk()
            self.status.info("Alert added: " + str(text)) 
        else:
            self.favourites.add(text)
            self.saveFavToDisk()
            self.status.info("Favourites added: " + str(text))
       


    #
    # downloaded data wazirx
    def processData(self, res): # res = arr_json
        unit = "usdt"
        list_market = []
        list_fav = []
        _json = json.loads(res)
        for key in _json.keys():
            if unit not in key:
                continue
            if _json[key]["open"] == "0.0":
                continue
            for favs in self.favourites:
                if favs in key:
                    list_fav.append(_json[key])
            list_market.append(_json[key])
        # alerts
        self.alerts.runAllRules(list_market)
        #data
        df_fav = pd.json_normalize(list_fav)
        df_market = pd.json_normalize(list_market)
        return (df_fav, df_market)

    #
    # runner in thread
    def thread_run(self, calling_container=None):
        url = "https://api.wazirx.com/api/v2/tickers"
        tup = ClientUtils.getData(url, self.processData, self.log, self.status)
        if tup is not None:
            (df_fav, df_market) = tup
            self.fav_df = df_fav
            self.market_df = df_market

    # 
    # click in List, slot
    def listItemClickedSlot(self, calling_container = None):
        print("item clicked")


    # get crypto data from yfinance:
    def getCryptoDataFromYf(self, name):
        yf_name = name.upper() + "-USD"
        df = yfinance.download(yf_name)
        if df.empty:
            return (None, None)
        else:
            info = yfinance.Ticker(yf_name).info
            return(df, info)

    def cellDoubleClicked(self, qmodelindex):
        clicked_data = qmodelindex.data()
        print("Clciked: " + str(clicked_data))
        if clicked_data.isalpha():
            self.clicked_crypto = clicked_data
            self.status.err("Please wait. Downloading data from yfinance...")
            (df, info) = self.getCryptoDataFromYf(self.clicked_crypto)
            if df is not None:
                msgbox = CryptoChartsDialogBox(df, info=info, parent=self)
                msgbox.exec()
                self.status.info("downloaded. done.")
            else:
                self.status.err("Error in downloading data, maybe crypto is delisted from YF")


    #
    # updateUI
    #
    @pyqtSlot()
    def updateUI(self):
        self.tab_container.tabChanged() # udpates ui



class WazirxAlerts:
    def __init__(self, parent=None, rule_num=0, symbol_rule = [], rate_rule = [], rule_list = []):
        self.parent = parent
        self.log = self.parent.log
        self.status = self.parent.status
        
        # rules
        self.rule_num = rule_num
        self.symbol_rule = symbol_rule
        self.rate_rule = rate_rule
        self.rule_list = rule_list
        
        # alert: $btc/r/>/.15
        # alert: $*/r/>/.1
        # alert: $btc/p/>/3000.000 usdt
    def parseTextForRule(self, text):
        if text[0] == '$':
            text = text[1:]
            rule_list = text.split("/")
            symbol = rule_list[0].strip()
            index = rule_list[1].strip()
            comparator = rule_list[2].strip()
            level = rule_list[3].strip()
            return (symbol, index, comparator, level)
        return None

    
    def addRules(self, rule_tuple):
        (symbol, index, comparator, level) = rule_tuple
        d = {}
        d["rule_tuple"] = rule_tuple
        d["rule_num"] = self.rule_num
        self.rule_num = self.rule_num + 1
        # btc/others can have a rate or price alert
        # but * can have only rate alert.
        if symbol == "*":
            self.rate_rule.append(d)            
        else:
            self.symbol_rule.append(d)
        self.status.info("Added: " + str(d))
    

    #
    # add alert
    def addAlert(self, text):
        rule_tuple = self.parseTextForRule(text)
        self.addRules(rule_tuple)
        

    # 
    # execute symbol based rule:
    def execSymbolRule(self, list_json, rule_dict):
        (symbol, index, comparator, level) = rule_dict["rule_tuple"]
        for _json in list_json:
            if symbol == _json["base_unit"]:
                if index == 'r':
                    _tocompare = float(_json["last"]) - float(_json["open"]) / float(_json["open"])
                else:
                    _tocompare = float(_json["last"])

                if comparator in ["gt", ">"]:
                    if _tocompare > float(level):
                        return [_json]
                    else:
                        return []
                
                if comparator in ["lt", "<"]:
                    if _tocompare < float(level):
                        return [_json]
                    else:
                        return []
        return []

    #
    # execute "all" rate comparision rule:
    def execRateRule(self, list_json, rule_dict):
        (symbol, index, comparator, level) = rule_dict["rule_tuple"]
        print(rule_dict["rule_tuple"])
        list_rule_crypto = []
        for _json in list_json:
            _rate = (float(_json["last"]) - float(_json["open"])) / float(_json["open"])
            print(_rate)
            print(level)
            if comparator in ["gt", ">"]:
                if _rate > float(level):
                    list_rule_crypto.append(_json)

            if comparator in ["lt", "<"]:
                if _rate < float(level):
                    list_rule_crypto.append(_json)
        return list_rule_crypto
    

    def runAllRules(self, list_rule):
        self.rule_list.clear()
        for rule_dict in self.symbol_rule:
            rule_dict["result"] = self.execSymbolRule(list_rule, rule_dict)
            self.rule_list.append(rule_dict)
        
        for rule_dict in self.rate_rule:
            rule_dict["result"] = self.execRateRule(list_rule, rule_dict)
            self.rule_list.append(rule_dict)



    

        
                        
                            
                    








app = QApplication(sys.argv)
screen = WazirxClient()
screen.show()
sys.exit(app.exec_())
    










# #
# # Main Window
# #
# class WazirxClientWindow(QWidget):
#     def __init__(self, parent=None):    # Main window in standalone, wont have any parent.
#         super(WazirxClientWindow, self).__init__()
#         self.parent = None
#         self.log = LoggingDialog()      # main window logger
#         self.status = LoggingStatus(self)
        
#         # config
#         self.update_interval = 60

#         # data 
#         self.favourite = set()              # favourite coins.
#         self.market_df = None               # dataframes
#         self.favourite_df = None

#         # ui component
#         self.input = AddFavourite(self)
#         self.tab = Tab(self)

#         # start:
#         self.setUI()

#         # thread
#         self.thread = ThreadDownloadData(self)
#         self.thread.signal_wazirx_data_download.connect(self.updateUI)
#         self.thread.start()

        
#     def setUI(self):
#         vbox = QVBoxLayout()
#         vbox.addWidget(self.input, 7)                       # input widget
#         vbox.addWidget(self.tab, 90)                        # tab widget
#         vbox.addWidget(self.status, 3)                      # status label
#         self.setLayout(vbox)

#     @pyqtSlot()
#     def updateUI(self):
#         self.tab.resetUpdateStatus()
#         self.tab.updateTab()

# #
# # Custom Widget
# #

# # widget for input and adding favourites.
# class AddFavourite(QWidget):
#     def __init__(self, parent=None):
#         super(AddFavourite, self).__init__()
#         self.parent = parent                # parent is window
#         self.log = self.parent.log          # LoggingDialog
#         self.status = self.parent.status    # QLabel
#         self.qle = QLineEdit()
#         self.btn = QPushButton("Add")
        
#         # call setting up UI
#         self.setUI()
    
#     def setUI(self):
#         hbox = QHBoxLayout()
#         hbox.addWidget(self.qle, 85)
#         hbox.addWidget(self.btn, 15)
#         self.setLayout(hbox)
#         self.btn.clicked.connect(self.addToFavourite)
        

#     @pyqtSlot()
#     def addToFavourite(self):
#         self.log.debug("adding favourite: " + self.qle.text())
#         fav_name = self.qle.text().strip()
#         self.log.debug("input: " + fav_name)
#         self.parent.favourite.add(fav_name)
#         self.status.setText("Favourite Added. Will see when refreshed in 1 min.")

# #
# # widget to show list of crypto, sorted by percent change
# class CryptoList(QTableView):
#     def __init__(self, parent=None):
#         super(QTableView, self).__init__()
#         self.parent = parent
#         self.log = self.parent.log
#         self.status = self.parent.status
#         self.setSortingEnabled(True)
        
#     # 
#     # table
#     def updateTable(self, df_crypto, default_text = None):
#         self.status.setText("updating table ...")
#         self.setModel(DataFrameModel(df_crypto))
#         self.status.setText("updated table.")

  
# #
# # tab widget -> favourite & market data
# class Tab(QTabWidget):
#     def __init__(self, parent=None):
#         super(Tab, self).__init__()
#         self.parent = parent
#         self.log = self.parent.log
#         self.status = self.parent.status
#         # ui
#         self.tab_name = ["Favourite", "Market"]
#         self.update_status = [False, False]
#         self.setUI()
#         self.currentChanged.connect(self.tabChanged)

#     def setUI(self):
#         self.addTab(CryptoList(self.parent), self.tab_name[0])
#         self.addTab(CryptoList(self.parent), self.tab_name[1])

#     def resetUpdateStatus(self):
#         self.update_status = [False, False]

      
#     def updateTab(self):
#         curr_index = self.currentIndex()
#         curr_widget= self.currentWidget()
#         if not self.update_status[curr_index]:
#             if curr_index == 0:
#                 self.log.debug("updating favourite tab ...")
#                 curr_widget.updateTable(self.parent.favourite_df, "No favourite found")
#             if curr_index == 1:
#                 self.log.debug("updating market data tab ...")
#                 curr_widget.updateTable(self.parent.market_df, "Error in loading data")    
#         self.update_status[curr_index] = True


#     @pyqtSlot()
#     def tabChanged(self):
#         """ update tab, if required. """
#         self.updateTab()



# # 
# # Thread
# class ThreadDownloadData(QThread):
#     signal_wazirx_data_download = pyqtSignal()
#     def __init__(self, parent =None):
#         super(ThreadDownloadData, self).__init__()
#         self.parent = parent
#         self.log = self.parent.log
#         self.status = self.parent.status
#         self.retry_interval = 20

#     def run(self):
#         while True:
#             arr_json = WazirxUtils.getData(log=self.parent.log)
#             self.log.debug("downloading wazirx data ...")
#             if arr_json is None:
#                 self.log.err("Could not download data from Wazirx")
#                 self.status.setText("Error Downloading Data.")
#                 time.sleep(self.retry_interval)
#                 continue

#             df = self.__convertJsonToDf(arr_json)
#             list_fav = []
#             for _json in arr_json:
#                 if _json["base_unit"] in self.parent.favourite:
#                     list_fav.append(_json)
            
#             fav_df = self.__convertJsonToDf(list_fav)

#             self.log.debug("downloaded wazirx data .. ")
#             self.parent.market_df = df
#             self.parent.favourite_df = fav_df
#             self.signal_wazirx_data_download.emit()
#             self.status.setText("downloaded wzx data and emitted...")
#             time.sleep(self.parent.update_interval)

#     def __convertJsonToDict(self, item):
#         d = {}
#         d["name"] = item["name"]
#         d["label_string"] = item["name"] + "\t" + str(item["price"]) + "\t" + str(item["chng"])
#         chng = float(item["chng"])
#         if chng < 0:
#             d["color"]="#ff0000"
#         else:
#             d["color"]="#00ff00"
#         d["json"] = item["json"]
#         return d

#     def __convertJsonToDf(self, arr_json):
#         df_keys = ["base_unit", "last", "open", "change", "volume"]
#         df = pd.json_normalize(arr_json)
#         print(df)
#         if not df.empty:
#             #df["change"] = df["last"] - df["open"] / df["open"]
#             return df[df_keys]
#         return df
                   
        


# app = QApplication(sys.argv)
# screen = WazirxClientWindow()
# screen.show()
# sys.exit(app.exec_())
    

