from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

import finplot as fplt
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.tz import gettz

import sip

#from widget_tab_container import TabContainer
from basic_custom_widgets import *



class ChartsClient:

    cs_keys = ["Open", "Close", "High", "Low"]
    ha_keys = ['h_open','h_close','h_high','h_low']
    ema_keys = ['Close']
    vma_keys = ['Volume']

    # rsi
    @classmethod
    def plotRsi(cls, df, ax, key="Close", period=1):
        diff = df[key].diff().values
        gains = diff
        losses = -diff
        with np.errstate(invalid='ignore'):
            gains[(gains<0)|np.isnan(gains)] = 0.0
            losses[(losses<=0)|np.isnan(losses)] = 1e-10 # we don't want divide by zero/NaN
        n = 14
        m = (n-1) / n
        ni = 1 / n
        g = gains[n] = np.nanmean(gains[:n])
        l = losses[n] = np.nanmean(losses[:n])
        gains[:n] = losses[:n] = np.nan
        for i,v in enumerate(gains[n:],n):
            g = gains[i] = ni*v + m*g
        for i,v in enumerate(losses[n:],n):
            l = losses[i] = ni*v + m*l
        rs = gains / losses
        df['rsi'] = 100 - (100/(1+rs))
        df.rsi.plot(ax=ax, legend='RSI')
        fplt.set_y_range(0, 100, ax=ax)
        fplt.add_band(30, 70, ax=ax)


    # ema
    @classmethod
    def plotEma(cls, df, ax, ema):   
        return df["Close"].ewm(span=ema).mean().plot(ax=ax, legend='EMA')
    
    # vma
    @classmethod
    def plot_vma(cls, df, ax):
        return df["Volume"].rolling(20).mean().plot(ax=ax, color='#c0c030')

    # ha   
    @classmethod
    def plotHA(cls, df, ax):
        df['h_close'] = (df.Open+df.Close+df.High+df.Low) / 4
        ho = (df.Open.iloc[0] + df.Close.iloc[0]) / 2
        for i,hc in zip(df.index, df['h_close']):
            df.loc[i, 'h_open'] = ho
            ho = (ho + hc) / 2
        print(df['h_open'])
        df['h_high'] = df[['High','h_open','h_close']].max(axis=1)
        df['h_low'] = df[['Low','h_open','h_close']].min(axis=1)
        return df[['h_open','h_close','h_high','h_low']].plot(ax=ax, kind='candle')

    # plot HA first.
    @classmethod
    def plot_heikin_ashi_volume(cls, df, ax):
        df[['h_open','h_close','volume']].plot(ax=ax, kind='volume')
    

    # plot cs
    @classmethod
    def plotCandles(cls, df, ax):
        #return df[["Open", "Close", "High", "Low"]].plot(ax=ax, kind="candle")
        return fplt.candlestick_ochl(df[cls.cs_keys], ax=ax)

    #
    # create blank graphics plotting widget
    @classmethod
    def blankGraphicsWidget(cls, alignment="horizontal", num_rows=1, init_zoom_periods=120):
        
        # fplt configuration.
        fplt.max_zoom_points = 5
        fplt.foreground = '#fff' # darkmode
        fplt.background = '#333'
        fplt.display_timezone = gettz('GMT') # time error fix.
    
        # Qt: to return Graphicsview
        graphics_view = QGraphicsView()
        
        if alignment == "horizontal":
            hbox = QHBoxLayout()
        else:
            hbox = QVBoxLayout()
    
        w = fplt.create_plot_widget(graphics_view.window(), rows=num_rows, init_zoom_periods=init_zoom_periods)
        
        list_axs = []
        
        if num_rows == 1:
            list_axs = [w]
        else:
            for i in w:
                list_axs.append(i)
        
        for i in list_axs:
            hbox.addWidget(i.ax_widget)
            i.set_visible(crosshair=True, xaxis=True, yaxis=True, xgrid=True, ygrid=True)
           
        graphics_view.window().axs = list_axs # finplot requres this property
        graphics_view.setLayout(hbox)
        return (graphics_view, w) # graphics view, list of ax


    #
    # plotting
    # all indicators are lists:
    #
    @classmethod
    def plotCandleStickChart(cls, df, plot_ha=False, ema=[], ema_ha=[], snr=[], alignment="horizontal", log=None, status=None, init_zoom_periods=120):
        if status:
            status.info("updating candlestick charts ...")
        if not plot_ha:
            (gv, list_ax) = cls.blankGraphicsWidget(alignment=alignment, num_rows=1, init_zoom_periods=init_zoom_periods)
            ax_candle = list_ax        
        else:
            (gv, list_ax) = cls.blankGraphicsWidget(alignment=alignment, num_rows=2, init_zoom_periods=init_zoom_periods)
            ax_candle = list_ax[0]
            ax_ha = list_ax[1]
            cls.plotHA(df, ax_ha)
            for ema_tf in ema_ha:
                cls.plotEma(df, ax_ha, ema_tf)
        print("---check :: --- ")
        print("gv " + str(sip.isdeleted(gv)))
        #print("flpt: " + str(sip.isdeleted(fplt)))
        cls.plotCandles(df, ax_candle)
        for ema_tf in ema:
            cls.plotEma(df, ax_candle, ema_tf)

        for price in snr:
            for i in range(-5, 5):
                fplt.add_line((0, price + i), (df.shape[0], price + i),  interactive=True)
        
        if status:
            status.info("updated candlestick charts.")
        
        print("gv " + str(sip.isdeleted(gv)))
        #print("gv " + str(sip.isdeleted(fplt)))
        #fplt.show(qt_exec=False) ## c/c++ object error
        #print(gv)
        #print(list_ax)
        return (gv, list_ax)

  


class ChartsScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super(QScrollArea, self).__init__()
        
        self.parent = parent
        self.log = self.parent.log
        self.status = self.parent.status

        self.setWidgetResizable(True)   # necessary
        self.setUI()
    
    def setUI(self):
        content_widget = QWidget()
        self.setWidget(content_widget)
        vbox = QVBoxLayout(content_widget)
        self.vbox = vbox 
        
    def addChart(self, qgv):
        self.vbox.addWidget(qgv)
    
    def removeAllChart(self):
        for i in reversed(range(self.vbox.count())):
            self.vbox.removeItem(self.vbox.itemAt(i))
    
    # to ignore scroll on wheel because
    # scroll wheel works in graphs
    def wheelEvent(self, ev):
        if ev.type() == QEvent.Wheel:
            ev.ignore()




#
#   takes in stock_info, it contains timeframes.
#   parent needs to have => stock_info and list_of_dataframes to chart.
#
class ChartsTabContainer(QWidget):
    def __init__(self, parent=None, stock_info=None, list_df=None, min_height=1000):
        super(ChartsTabContainer, self).__init__()
        self.parent = parent
        self.log = self.parent.log
        self.status = self.parent.status
        
        # info
        self.min_height = min_height

        # data from parent:
        self.stock_info = self.parent.stock_info
        # df is also from parent. used directly, because it changes.

        # tabs:
        self.tab_container = TabContainer(tab_list=self.allTab(), parent=self)

        # ui
        self.setUI()

    def setUI(self):
        vbox = QVBoxLayout()
        vbox.addWidget(self.tab_container)
        self.setLayout(vbox)

    
    def allTab(self):
        list_tabs = []
        for tf in self.stock_info.timeframes:
            d = TabContainer.createTabDict(
                name = str(tf) + " MIN",
                widget = ChartsScrollArea(self),
                slot = self.tabChangedSlot_UpdateCharts 
            )
            list_tabs.append(d)
        return list_tabs
        

    #
    # function that updates the chart, everytime we visit this tab.
    # calling_container == QTabWidget
    #
    #
    def tabChangedSlot_UpdateCharts(self, widget, calling_container=None):
        widget.removeAllChart()     # widget = the first parent widget inside tab === ChartsArea.
        if self.parent.df is not None:
            (gv, list_ax) = ChartsClient.plotCandleStickChart(self.parent.df[calling_container.currentIndex()],
                                                     alignment="vertical", 
                                                     ema=[10, 20, 50, 100], status=self.status)
            gv.setMinimumHeight(self.min_height)   
            widget.addChart(gv)
            if self.status:
                self.status.info("tabChangedSlot: updated chart..")  
        else:
            if self.status:
                self.status.info("tabChangedSlot: error -> df is none.")                                     
        


class CryptoChartsDialogBox(QDialog):
    def __init__(self, df, info=None, parent=None):
        super(CryptoChartsDialogBox, self).__init__()
        #self.setSizeGripEnabled (True)
        (self.parent, self.log, self.status) = setUpParent(parent)
        self.df = df
        self.info = info
        self.charts_scroll_area = ChartsScrollArea(parent=self.parent)
        print(sip.isdeleted(self.charts_scroll_area))
       
        (gv, list_ax) = ChartsClient.plotCandleStickChart(  self.df,
                                                            alignment="vertical", 
                                                            ema=[10, 20, 50, 100], status=self.status,
                                                            init_zoom_periods=240)
        
        self.charts_scroll_area.minimumWidth = 600
        self.charts_scroll_area.minimumWidth = 600
        self.charts_scroll_area.move(30, 80)
        self.setWindowTitle('Hello MessageBox ???')
        #self.setIcon(self.Question)
        #self.setText("Hello MessageBox")
       
        gv.minimumWidth= 500
        gv.minimumWidth= 500
        
        self.charts_scroll_area.removeAllChart()
        self.charts_scroll_area.addChart(gv)
        self.gv = gv

        print(sip.isdeleted(self.gv))
        print(sip.isdeleted(self))
        
        self.setChartsUI()
        
        #self.exec_()

    def setChartsUI(self):
        vbox = QVBoxLayout()
        if self.info is not None:
            vbox.addWidget(self.charts_scroll_area, 80)
            vbox.addWidget(self.setInfoUI(self.info), 20)
        else:
           vbox.addWidget(self.charts_scroll_area)         
        self.setLayout(vbox)
    
    def setInfoUI(self, info):
        string = "name: {name}\ndesc: {desc}\n".format(name=info["name"], desc=info["description"])
        ql = QLabel()
        ql.setWordWrap(True)
        ql.setText(string)
        return ql
        

    # def event(self, e):
    #     result = QMessageBox.event(self, e)
    #     self.setMinimumWidth(0)
    #     self.setMaximumWidth(16777215)
    #     self.setMinimumHeight(0)
    #     self.setMaximumHeight(16777215)
    #     self.setSizePolicy(
    #         QSizePolicy.Expanding, 
    #         QSizePolicy.Expanding
    #     )
    #     self.resize(700, 700)


        


