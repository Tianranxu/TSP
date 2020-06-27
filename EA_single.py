import numpy as np
from datetime import datetime
import pandas as pd
import math


def getData():
    return pd.read_csv('./in_data/SP----C.csv', names=['date', 'open', 'high', 'low', 'close', 'volume', 'open_volume'])
    #return pd.read_csv('./out.csv', header=0)


def getLag(data, time_const):
    lag = []
    last_lag = data[0]
    for d in data:
        current_lag = float(last_lag + (d - last_lag)*2 / (time_const + 1))
        lag.append(current_lag)
        last_lag = current_lag
    return lag


def calculateTrade(data):
    trade_info = []
    for index, d in data.iterrows():
        if index == 25:
            last_lag_diff = d.fast_lag - d.slow_lag
        elif index > 25:
            current_lag_diff = d.fast_lag - d.slow_lag
            if (last_lag_diff >= 0 and current_lag_diff < 0 and len(trade_info) > 0):  # sell
                if index < len(data) - 1:
                    trade_info.append([int(data.loc[index + 1, 'date']), float((data.loc[index + 1].open + data.loc[index + 1, 'low']) / 2), 'Exit'])
            elif (last_lag_diff <= 0 and current_lag_diff > 0):  # buy
                if index == len(data) - 1: #最后一天触发buy
                    trade_info.append([int(data.loc[index, 'date']), float((data.loc[index].open + data.loc[index, 'high']) / 2), 'Entry'])
                else:
                    trade_info.append([int(data.loc[index + 1, 'date']), float((data.loc[index + 1].open + data.loc[index + 1, 'high']) / 2), 'Entry'])
            last_lag_diff = current_lag_diff
        if index == len(data) - 1 and len(trade_info) >= 1 and trade_info[-1][2] == 'Entry':
            trade_info.append([int(d.date), float(d.close), 'Exit'])
    trade = pd.DataFrame(columns=['date', 'price', 'note'], data=trade_info)
    #trade.to_csv('trade.csv', index=0)
    return trade


def getATR(data):
    ture_range = []
    last_close = data.iloc[0].close
    for index, d in data.iterrows():
        ture_range.append(max(d.high, last_close) - min(d.low, last_close))
        last_close = d.close
    return getLag(ture_range, 20)


def getPositionAndProfit(trade_info, equity, heat):
    position_size = []
    profit = []
    for index, t in trade_info.iterrows():
        if t.note == 'Entry':
            current_atr_index = data[data.date == t.date].index.values
            last_atr = data.iloc[current_atr_index[0] - 1].atr
            temp_position = equity * heat / (last_atr * 5)
            unit = int(temp_position / 250)
            unit = unit + 1 if temp_position % 250 > 125 else unit
            temp_position = unit * 250
            position_size.append(temp_position)
            last_date = t.date
            last_price = t.price
        elif t.note == 'Exit':
            profit.append([temp_position, last_date, last_price, t.date, t.price,
                           round(temp_position * (t.price - last_price), 3)])
            equity = equity + temp_position * (t.price - last_price)
    return pd.DataFrame(columns=['unit', 'entry_date', 'entry_price', 'exit_date', 'exit_price', 'profit'], data=profit)


def getEquityLog(data, profit, init_equity):
    equity = pd.DataFrame(columns=['date'], data=data.date)
    entry_info = profit.set_index('entry_date')
    exit_info = profit.set_index('exit_date')
    equity['close_balance'] = init_equity
    equity['open_profit'] = 0.00
    equity['equity'] = init_equity
    current_unit = 0
    entry_price = 0.00
    close_balance = init_equity
    for index, d in data.iterrows():
        if d.date in profit['entry_date'].values:
            current_unit = entry_info.loc[d.date].unit
            entry_price = entry_info.loc[d.date].entry_price
        if d.date in profit['exit_date'].values:
            current_unit = 0
            close_balance = close_balance + exit_info.loc[d.date, 'profit']
        # print(equity.loc[index, 'date'])
        open_profit = round(current_unit * (d.close - entry_price), 3)
        equity.loc[index, 'equity'] = open_profit + close_balance
        equity.loc[index, 'open_profit'] = open_profit
        equity.loc[index, 'close_balance'] = close_balance
    return equity


def getPercentDrawDown(equity):
    peak = 0
    max_draw_down = 0
    for index, e in equity.iterrows():
        if peak < e.equity:
            peak = e.equity
        current_draw_down = (peak - e.equity) / peak
        if current_draw_down > max_draw_down:
            max_draw_down = current_draw_down
    return max_draw_down


def getICAGR(equity):
    ratio = equity.loc[len(equity) - 1, 'equity'] / equity.loc[0, 'equity']
    start_date = str(equity.loc[0, 'date'])
    start_date = datetime.strptime(start_date, '%Y%m%d')
    end_date = str(equity.loc[len(equity) - 1, 'date'])
    end_date = datetime.strptime(end_date, '%Y%m%d')
    d = end_date - start_date
    years = d.days / 365.25
    icagr = 0
    try:
        icagr = round(math.log(ratio) / years, 5)
    except Exception as ex:
        print('ratio', ratio)
    return icagr


filenames = ['JY_B.CSV', 'GC2_B.CSV', 'ED_B.CSV', 'CT2_B.CSV', 'CL2_B.CSV',
             'BP_B.CSV', 'US_B.CSV', 'SB2_B.CSV', 'S2_B.CSV', 'PL2_B.CSV', 'LC_B.CSV']
for i, f in enumerate(filenames):
    filenames[i] = './in_data/' + f

for file in filenames:
    data = pd.read_csv(file, names=['date', 'open', 'high', 'low', 'close', 'volume', 'open_volume'], usecols=[0, 1, 2, 3, 4, 5, 6])
    data['fast_lag'] = getLag(data.close, 20)
    data['slow_lag'] = getLag(data.close, 300)
    trade_info = calculateTrade(data)
    data['atr'] = getATR(data)
    equity = 2000000.00
    heat = 0.02
    profit = getPositionAndProfit(trade_info, equity, heat)
    equity_log = getEquityLog(data, profit, equity)
    icagr = getICAGR(equity_log)
    pdd = getPercentDrawDown(equity_log)
    print('file:', file, 'icagr:', icagr, 'pdd:', pdd, 'bliss:', icagr / pdd)
# data = getData()
# data['fast_lag'] = getLag(data.close, 15)
# data['slow_lag'] = getLag(data.close, 150)
# trade_info = calculateTrade(data)
# data['atr'] = getATR(data)
# equity = 2000000.00
# heat = 0.02
# profit = getPositionAndProfit(trade_info, equity, heat)
# profit.to_csv('trade.csv')
# data = getEquityLog(data, profit, equity)
# equity_log = data[['date', 'close_balance', 'open_profit', 'equity']]
# equity_log.to_csv('equityLog.csv')


# print('file:', file, 'bliss:', icagr / pdd)
# equity_log.to_csv('equityLog'+file)
