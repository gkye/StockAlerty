from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import backtrader as bt
import datetime
from datetime import timedelta
import backtrader.indicators as btind
import json

class BaseStrategy(bt.Strategy):
    
    def __init__(self, auto_buy_sell=False, notify_no_pos_sell=True):
        self.dataclose= self.datas[0].close    # Keep a reference to the "close" line in the data[0] dataseries
        self.order = None # Property to keep track of pending orders.  There are no orders when the strategy is initialized.
        self.buyprice = None
        self.buycomm = None
        self.algoName = "Base"
        self.auto_buy_sell = auto_buy_sell 
        self.notify_no_pos_sell = notify_no_pos_sell
        self.sold_order_ids = []
        self.bought_order_ids = []
        self.bar_executed = 0

    
    def log(self, txt, dt=None):
        # Logging function for the strategy.  'txt' is the statement and 'dt' can be used to specify a specific datetime
        dt = dt or self.datas[0].datetime.date(0)
        # print('{0},{1}'.format(dt.isoformat(),txt))
        print(txt)
    
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # print(order.ref)
        status_str = 'BUY'
        is_buy = True
        icon = "🎯"

        if order.ref in self.sold_order_ids:
            status_str = 'SOLD'
            is_buy = False
            icon = "💵 "

        self.log('{} Algo {}: {} {} @ {}. Value: {} | Commissions: {} | {}'\
            .format(icon, self.algoName, status_str, self.datas[0]._name,
                self.order.executed.price, self.order.executed.value, self.order.executed.comm, self.datas[0].datetime.date(0)))
        print("-"*100)
        
        if not order.alive():
            self.order = None 
    
    def next(self):
        print(11)

    def store_order(self, order, is_buy):
        order_dict = {
            "time": self.datas[0].datetime.date(0).strftime("%Y-%m-%d %H:%M:%S"),
            "ticker": "",
            "algo": self.algoName,
            "price_total": order.executed.price,
            "value": order.executed.value,
            "comm": order.executed.comm,
        }

        if is_buy is True:
            order_dict["type"] = "purchase"
        else:
            order_dict["type"] = "sale"


    def buy_notify(self, data):
        if self.auto_buy_sell:
            if not self.position:
                self.order = self.buy()
                self.bought_order_ids.append(self.order.ref)
        else:
            self.log('🎯  Algo {}: Buy {} @ {}'.format(self.algoName, data._name, data.close[0]))
    
    def sale_notify(self, data):
        if self.auto_buy_sell:
            if self.position:
                self.order = self.sell()
                self.sold_order_ids.append(self.order.ref)
        else:
            self.log('💵  Algo {}: SELL {} @ {}'.format(self.algoName, data._name, data.close[0]))
  

class RSI(BaseStrategy):

    def __init__(self):
        BaseStrategy.__init__(self)
        self.algoName = "RSI"
        self.rsi = bt.indicators.RSI_SMA(self.data.close, period=14)
            
    def next(self):
        for i, data in enumerate(self.datas):
            if self.order:
                break
            rsi_over = self.rsi > 70
            rsi_under = self.rsi < 30
    
            if rsi_under:
                self.buy_notify(data)
            if rsi_over:
                self.sale_notify(data)
            
               
class SMA_One(BaseStrategy):
    def __init__(self):
        BaseStrategy.__init__(self)
        self.algoName = "SMA"

    def next(self):
        for i, data in enumerate(self.datas):
            if self.order:
                break
                
            is_buy = self.dataclose[0] < self.dataclose[-1] and self.dataclose[-1] < self.dataclose[-2]
            is_sell = len(self) >= (self.bar_executed+5)
            if is_buy is True:
                self.buy_notify(data)
            
            if is_sell is True:
                self.sale_notify(data)


class FixedPerc(bt.Sizer):
    '''This sizer simply returns a fixed size for any operation

    Params:
      - ``perc`` (default: ``0.20``) Perc of cash to allocate for operation
    '''

    params = (
        ('perc', 0.20),  # perc of cash to use for operation
    )

    def _getsizing(self, comminfo, cash, data, isbuy):
        cashtouse = self.p.perc * cash
        if BTVERSION > (1, 7, 1, 93):
            size = comminfo.getsize(data.close[0], cashtouse)
        else:
            size = cashtouse // data.close[0]
        return size


class Macd(BaseStrategy):
    '''
    This strategy is loosely based on some of the examples from the Van
    K. Tharp book: *Trade Your Way To Financial Freedom*. The logic:

      - Enter the market if:
        - The MACD.macd line crosses the MACD.signal line to the upside
        - The Simple Moving Average has a negative direction in the last x
          periods (actual value below value x periods ago)

     - Set a stop price x times the ATR value away from the close

     - If in the market:

       - Check if the current close has gone below the stop price. If yes,
         exit.
       - If not, update the stop price if the new stop price would be higher
         than the current
    '''

    params = (
        # Standard MACD Parameters
        ('macd1', 12),
        ('macd2', 26),
        ('macdsig', 9),
        ('atrperiod', 14),  # ATR Period (standard)
        ('atrdist', 3.0),   # ATR distance for stop price
        ('smaperiod', 30),  # SMA Period (pretty standard)
        ('dirperiod', 10),  # Lookback period to consider SMA trend direction
    )

    def __init__(self):
        BaseStrategy.__init__(self)
        self.algoName = "MCAD"
        self.macd = bt.indicators.MACD(self.data,
                                       period_me1=self.p.macd1,
                                       period_me2=self.p.macd2,
                                       period_signal=self.p.macdsig)

        # Cross of macd.macd and macd.signal
        self.mcross = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)

        # To set the stop price
        self.atr = bt.indicators.ATR(self.data, period=self.p.atrperiod)

        # Control market trend
        self.sma = bt.indicators.SMA(self.data, period=self.p.smaperiod)
        self.smadir = self.sma - self.sma(-self.p.dirperiod)
        self.pstop = 0

    def start(self):
        self.order = None  # sentinel to avoid operrations on pending order

    def next(self):
        for i, data in enumerate(self.datas):
            self.order_ticker = data._name
            if self.order:
                break
            
            if not self.position:  # not in the market
                if self.mcross[0] > 0.0 and self.smadir < 0.0:
                    self.buy_notify(data)
                    pdist = self.atr[0] * self.p.atrdist
                    self.pstop = self.data.close[0] - pdist
                    
            else:  # in the market
                pclose = self.data.close[0]
                pstop = self.pstop

                if pclose < pstop:
                    self.sale_notify(data)  # stop met - get out
                else:
                    pdist = self.atr[0] * self.p.atrdist
                    # Update only if greater than
                    self.pstop = max(pstop, pclose - pdist)

class OutputStrategy(bt.Strategy):

    def _print_current_bar_price(self, data):
        txt = list()
        txt.append(data._name)
        txt.append('%04d' % len(data))
        txt.append('%s' % datetime.datetime.now().time())
        txt.append('%s' % data.datetime.datetime(0))
        txt.append('{}'.format(data.open[0]))
        txt.append('{}'.format(data.high[0]))
        txt.append('{}'.format(data.low[0]))
        txt.append('{}'.format(data.close[0]))
        txt.append('{}'.format(data.volume[0]))
        print(', '.join(txt))

    def __init__(self):
        self._count = [0] * len(self.datas)

    def notify_data(self, data, status, *args, **kwargs):
        print('*' * 5, data._name, ' data is ', data._getstatusname(status), *args)

    def notify_store(self, msg, *args, **kwargs):
        print('*' * 5, 'STORE NOTIF:', msg)

    def prenext(self):
        # call next() even when data is not available for all tickers
        self.next()

    def next(self):
        # run on the symbols
        for i, d in enumerate(self.datas):
            if len(d) > self._count[i]:
                self._count[i] = len(d)
                self._print_current_bar_price(d)