from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import backtrader as bt
import datetime
from datetime import timedelta    
from strags import *

def setup_cerbo(tickers, from_date, to_date, budget, stake, isLive=False, tws_store=None):
    cerebro = bt.Cerebro()  # We initialize the `cerebro` backtester.
    cerebro.addstrategy(RSI)
    cerebro.addstrategy(Macd)
    cerebro.addstrategy(SMA_One)
    cerebro.addstrategy(OutputStrategy)

    if to_date is None:
        to_date = datetime.datetime.now()
    
    for ticker in tickers:
        data = None
        if tws_store is not None:
            historical = isLive == False
            if isLive:
                data = tws_store.getdata(dataname=ticker, timeframe=bt.TimeFrame.Seconds, compression=1, qcheck=1, backfill_start=False, backfill= True)
            else:
                data = tws_store.getdata(historical=True, dataname=ticker, fromdate=from_date, todate=to_date)
                
        else:
            data = bt.feeds.YahooFinanceData(dataname=ticker, fromdate=from_date, todate=to_date)

        if data is not None:
            cerebro.adddata(data, name=ticker)

    if tws_store is not None:
        cerebro.broker = tws_store.getbroker()
    else:
        cerebro.broker.setcash(budget) 
        cerebro.broker.setcommission(commission=0.002) # We set broker comissions of 0.1%

    
    # Add a FixedSize sizer according to the stake
    cerebro.addsizer(bt.sizers.FixedSize, stake=stake)
    return cerebro

def back_test(tickers, from_date, to_date, budget, stake, isLive=False):
    cerebro = setup_cerbo(tickers=tickers, from_date=from_date, to_date=to_date, budget=budget, stake=stake, isLive=isLive)
    
    starting_value = float('{0:8.2f}'.format(cerebro.broker.getvalue()))
    print('Starting Portfolio Value: {0:8.2f}'.format(cerebro.broker.getvalue()))
    cerebro.run(runonce=False, preload=True)

    print('Final Portfolio Value: {0:8.2f}'.format(cerebro.broker.getvalue()))
    ending_value = float('{0:8.2f}'.format(cerebro.broker.getvalue()))

    profit = ending_value - starting_value
    print('Profit: {0:8.2f}'.format(profit))

def ib_live_notify(tickers, from_date, to_date, budget, stake, isLive=False):
    store = bt.stores.IBStore(port=4002, _debug=False)
    cerebro = setup_cerbo(tickers=tickers, from_date=from_date, to_date=to_date, budget=budget, stake=stake, isLive=isLive, tws_store=store)

    cerebro.run(runonce=False, preload=True)
    # store.connectionClosed(msg='222')

        
if __name__ == '__main__':
    #TODO: Flask server for app & rabbit mq to handle tasks
    #TODO: Show backtesting data for outout
    #TODO: Create stop orders and limit orders
    
    contracts = [
        'EUR.USD-CASH-IDEALPRO',
        'SNDL-STK-ISLAND-USD',
        'PFE-STK-SMART-USD'
    ]
    ib_live_notify(tickers=contracts, from_date=datetime.datetime(2020, 1, 1), to_date=None, budget=5000, stake=1, isLive=True)

