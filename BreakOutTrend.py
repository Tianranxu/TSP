# -*- coding: UTF-8 -*-
import datetime
import pandas as pd
import math
import config

class BOT(object):
    def __init__(self, filenames, setting):
        self.files = filenames
        self.setting = setting
        self.icagr = 0.00
        self.max_draw_down = 0.00
        self.bliss = 0.00

    def initTmp(self):
        # 作用为全局临时变量
        self.current_position = []
        self.current_data = []
        self.current_status = []
        self.last_date = []
        self.last_data = []
        self.entry_price = []
        for num in range(0, self.setting['count'], 1):
            self.current_data.append(0)
            self.last_data.append(0)
            self.current_position.append(0)
            self.last_date.append(0)
            self.entry_price.append(0.00)
            self.current_status.append('flat')

    def setData(self):
        self.data = []
        self.trade_info = []
        self.point_value = []
        self.data_d = []
        for i, f in enumerate(self.files):
            self.data.append(pd.read_csv(f, index_col=0))
            fname = f.split('.')[1].split('/')[3]
            self.point_value.append(config.PointValue[fname])
            self.trade_info.append(pd.DataFrame(columns=['date', 'price', 'note', 'status', 'data_index', 'instru']))
            self.calculateTrade(i)
            self.trailingStopLoss(i)
            self.data_d.append(self.data[i].set_index('date'))  # 以date为index，加快运算速度

    def getLag(self, prices, time_const):
        lag = []
        last_lag = prices[0]
        for d in prices:
            current_lag = float(last_lag + (d - last_lag) * 2 / (time_const + 1))
            lag.append(current_lag)
            last_lag = current_lag
        return lag

    def trade(self, index, data_i, status, note):
        if data_i < len(self.data[index]) - 1:  # 最后一天触发买卖,不加1
            data_i = data_i + 1
        data = self.data[index].loc[data_i]
        date = int(data.date)
        price = 0  # 无意义的初始化
        if (note == 'exit' and status == 'long') or (note == 'entry' and status == 'short'):
            price = data.open - (data.open - data.low) * self.setting['slippage_factor']
        elif (note == 'exit' and status == 'short') or (note == 'entry' and status == 'long'):
            price = data.open + (data.high - data.open) * self.setting['slippage_factor']
        self.trade_info[index].loc[self.trade_info[index].shape[0]] = {'date': date, 'price': price, 'note': note,
                                                            'status': status, 'data_index': data_i, 'instru': index}
        return

    def calculateTrade(self, index):
        current_status = 'flat'
        for i, d in self.data[index].iterrows():
            if i < self.setting['warm_up_days']:  # warm up
                continue

            if d.close >= d.last_high1:
                if current_status == 'long':
                    if d.close <= d.last_low2:
                        self.trade(index, i, 'long', 'exit')
                        current_status = 'flat'
                elif current_status == 'flat':
                    if d.fast_lag > d.slow_lag:  # trend up
                        self.trade(index, i, 'long', 'entry')
                        current_status = 'long'
                elif current_status == 'short':
                    if d.close >= d.last_high2:
                        if d.fast_lag > d.slow_lag:  # trend up
                            self.trade(index, i, 'short', 'exit')
                            self.trade(index, i, 'long', 'entry')
                            current_status = 'long'
                        elif d.fast_lag <= d.slow_lag:  # trend down
                            self.trade(index, i, 'short', 'exit')
                            current_status = 'flat'

            elif d.close <= d.last_low1:
                if current_status == 'long':
                    if d.close <= d.last_low2:
                        if d.fast_lag >= d.slow_lag:  # trend up
                            self.trade(index, i, 'long', 'exit')
                            current_status = 'flat'
                        elif d.fast_lag < d.slow_lag:  # trend down
                            self.trade(index, i, 'long', 'exit')
                            self.trade(index, i, 'short', 'entry')
                            current_status = 'short'
                elif current_status == 'flat':
                    if d.fast_lag < d.slow_lag:  # trend down
                        self.trade(index, i, 'short', 'entry')
                        current_status = 'short'
                elif current_status == 'short':
                    if d.close >= d.last_high2:
                        if d.fast_lag > d.slow_lag:  # trend up
                            self.trade(index, i, 'short', 'exit')
                            self.trade(index, i, 'long', 'entry')
                            current_status = 'long'
                        elif d.fast_lag <= d.slow_lag:  # trend down
                            self.trade(index, i, 'short', 'exit')
                            current_status = 'flat'

            trade_len = len(self.trade_info[index])
            if i == len(self.data[index]) - 1 and trade_len >= 1 \
                    and self.trade_info[index].loc[trade_len-1, 'note'] == 'entry':
                self.trade(index, i, self.trade_info[index].loc[trade_len-1, 'status'], 'exit')
        return

    def trailingStopLoss(self, index):
        ind_t = 0
        self.data[index]['trailing_stop'] = 0
        while ind_t < len(self.trade_info[index]) - 1:
            entry = self.trade_info[index].loc[ind_t]
            exit = self.trade_info[index].loc[ind_t + 1]
            start = entry.data_index
            end = exit.data_index
            price_high = 0
            price_low = 0
            trailing_stop = 0
            for i in range(start, end + 1):
                data = self.data[index].iloc[i]
                if entry.status == 'long':
                    if i == start:
                        price_high = data.close
                        trailing_stop = price_high - self.setting['ts_multiplier'] * data.atr
                        continue
                    if price_high < data.close:
                        price_high = data.close
                    if trailing_stop < price_high - self.setting['ts_multiplier'] * data.atr:
                        trailing_stop = price_high - self.setting['ts_multiplier'] * data.atr
                    self.data[index].loc[i, 'trailing_stop'] = trailing_stop
                    if data.close <= trailing_stop and i < len(self.data[index]) - 1:
                        next = self.data[index].iloc[i + 1]
                        self.trade_info[index].loc[ind_t + 1, 'date'] = int(next.date)
                        self.trade_info[index].loc[ind_t + 1, 'price'] = next.open + (next.open - next.low) * \
                                                                         self.setting['slippage_factor']
                        break

                elif entry.status == 'short':
                    if i == start:
                        price_low = data.close
                        trailing_stop = price_low + self.setting['ts_multiplier'] * data.atr
                        continue
                    if price_low > data.close:
                        price_low = data.close
                    if trailing_stop > price_low + self.setting['ts_multiplier'] * data.atr:
                        trailing_stop = price_low + self.setting['ts_multiplier'] * data.atr
                    self.data[index].loc[i, 'trailing_stop'] = trailing_stop
                    if data.close >= trailing_stop and i < len(self.data[index]) - 1:
                        next = self.data[index].iloc[i + 1]
                        self.trade_info[index].loc[ind_t + 1, 'date'] = int(next.date)
                        self.trade_info[index].loc[ind_t + 1, 'price'] = next.open + (next.high - next.open) * \
                                                                         self.setting['slippage_factor']
                        break
            ind_t = ind_t + 2

    def getATR(self, ind, period):
        ture_range = []
        last_close = self.data[ind].iloc[0].close
        for index, d in self.data[ind].iterrows():
            ture_range.append(max(d.high, last_close) - min(d.low, last_close))
            last_close = d.close
        return self.getLag(ture_range, period)

    def generateTradeLog(self):
        for index, t in enumerate(self.trade_info):
            if index == 0:
                self.trade_log = t
            else:
                self.trade_log = self.trade_log.append(t)
        self.trade_log = self.trade_log.sort_values('date')
        self.trade_log = self.trade_log.reset_index(drop=True)
        self.trade_log['unit'] = 0

    def profitSum(self):
        profitSum = []
        self.totalProfit = 0
        for num in range(0, self.setting['count'], 1):
            profitSum.append([self.files[num], 0])
        for index, p in self.profit.iterrows():
            profitSum[int(p.instru)][1] = profitSum[int(p.instru)][1] + p.profit
            self.totalProfit = self.totalProfit + p.profit
        for num in range(0, self.setting['count'], 1):
            profitSum[num][1] = round(profitSum[num][1], 4)
            profitSum[num].append(round(profitSum[num][1] / self.totalProfit, 4))
        self.profitSum = pd.DataFrame(columns=['file', 'profit', 'rate'], data=profitSum)

    def getMergeDate(self):
        date_set = set([])
        for d in self.data:
            temp_set = set(d.date.astype('int'))
            date_set = date_set | temp_set
        date_list = list(date_set)
        date_list.sort()
        return date_list

    def getRiskPerLot(self, data, index, status):
        risk_per_lot_trailing = 0
        if status == 'long':
            risk_per_lot_inherent = (data.close - data.last_low2) * self.point_value[index]
            if data.trailing_stop != 0:
                risk_per_lot_trailing = (data.close - data.trailing_stop) * self.point_value[index]
        elif status == 'short':
            risk_per_lot_inherent = (data.last_high2 - data.close) * self.point_value[index]
            if data.trailing_stop != 0:
                risk_per_lot_trailing = (data.trailing_stop - data.close) * self.point_value[index]
        return risk_per_lot_inherent if risk_per_lot_inherent > risk_per_lot_trailing else risk_per_lot_trailing

    def getVolatilityPerLot(self, data, index):
        return data.atr * self.point_value[index]

    def getUnitByRisk(self, equity, risk_per_lot):
        return math.floor(equity * self.setting['initial_risk_budget'] / risk_per_lot)

    def getUnitByVolatility(self, equity, volatility_per_lot):
        return int(equity * self.setting['initial_risk_budget'] / volatility_per_lot)

    def getInitPosition(self, equity, trade):
        risk_per_lot = self.getRiskPerLot(self.last_data[trade.instru], trade.instru, trade.status)
        volatility_per_lot = self.getVolatilityPerLot(self.last_data[trade.instru], trade.instru)
        initial_units_by_risk = self.getUnitByRisk(equity, risk_per_lot)
        initial_units_by_volatility = self.getUnitByVolatility(equity, volatility_per_lot)
        units = initial_units_by_risk if initial_units_by_risk > initial_units_by_volatility else initial_units_by_volatility
        return units * self.point_value[trade.instru]

    def OnGoingPositionSizing(self, equity, close_balance):
        total_risk = 0.0
        for i, x in enumerate(self.current_position):
            if x != 0:
                risk_per_lot = self.getRiskPerLot(self.last_data[i], i, self.current_status[i])
                if risk_per_lot == 0:
                    continue
                volatility_per_lot = self.getVolatilityPerLot(self.last_data[i], i)
                units_by_risk = self.getUnitByRisk(equity, risk_per_lot)
                units_by_volatility = self.getUnitByVolatility(equity, volatility_per_lot)
                total_risk += risk_per_lot * (self.current_position[i] / self.point_value[i])
                current_units = self.current_position[i] / self.point_value[i]
                if current_units < units_by_risk or self.current_position[i] < units_by_volatility:
                    ongoing_units = units_by_risk if units_by_risk < units_by_volatility else units_by_volatility
                    exit_price = self.current_data[i].open + (self.current_data[i].high - self.current_data[i].open)*self.setting['slippage_factor']
                    adjust_units = self.current_position[i] - ongoing_units
                    self.current_position[i] = ongoing_units * self.point_value[i]
                    if self.current_status[i] == 'long':
                        close_balance += adjust_units * (exit_price - self.entry_price[i])
                    elif self.current_status[i] == 'short':
                        close_balance -= adjust_units * (exit_price - self.entry_price[i])
        # total_risk_ratio = total_risk / equity
        # if total_risk_ratio > self.setting['total_open_market_risk_limit']:
        return close_balance, total_risk

    def onGoningTrade(self):
        self.initTmp()
        self.equity_log = pd.DataFrame(columns=['date'], data=self.getMergeDate())
        self.equity_log['close_balance'] = self.setting['equity']
        self.equity_log['open_profit'] = 0.00
        self.equity_log['equity'] = self.setting['equity']
        self.equity_log['total_risk'] = 0.00
        close_balance = self.setting['equity']
        last_equity = self.setting['equity']
        # 在equity_log 和 trade_log 这两个循环里面，预设两边最后一个date是相同的，如果有不同的情况需要修改
        index_t = 0
        current_trade = self.trade_log.iloc[index_t]
        for ind, d in self.equity_log.iterrows():
            # update current data
            for i, x in enumerate(self.current_data):
                try:
                    self.current_data[i] = self.data_d[i].loc[d.date, ['open', 'close', 'atr', 'high', 'trailing_stop', 'last_high2', 'last_low2']]
                except Exception as ex:
                    # print('equity date miss', i, d.date)
                    continue
            # on going position sizing
            close_balance, total_risk = self.OnGoingPositionSizing(last_equity, close_balance)
            if ind > 0:
                self.equity_log.loc[ind - 1, 'total_risk'] = total_risk

            # position init   # current_trade: 'date', 'price', 'note', 'status', 'data_index', 'instru'
            while d.date == current_trade.date and index_t < len(self.trade_log):
                if current_trade.note == 'entry':
                    self.entry_price[current_trade.instru] = current_trade.price
                    self.current_status[current_trade.instru] = current_trade.status
                    self.current_position[current_trade.instru] = self.getInitPosition(last_equity,  current_trade)
                if current_trade.note == 'exit':
                    if self.current_status[current_trade.instru] == 'long':
                        close_balance += self.current_position[current_trade.instru] * (
                            current_trade.price - self.entry_price[current_trade.instru])
                    elif self.current_status[current_trade.instru] == 'short':
                        close_balance -= self.current_position[current_trade.instru] * (
                                current_trade.price - self.entry_price[current_trade.instru])
                    self.entry_price[current_trade.instru] = 0
                    self.current_position[current_trade.instru] = 0
                    self.current_status[current_trade.instru] = 0
                index_t = index_t + 1
                try:
                    current_trade = self.trade_log.iloc[index_t]
                except Exception as ex:
                    break

            # equity calculate
            open_profit = 0
            for i, x in enumerate(self.current_position):
                self.last_data[i] = self.current_data[i]
                if x != 0:
                    if self.current_status[i] == 'long':
                        open_profit += x * (self.current_data[i].close - self.entry_price[i])
                    elif self.current_status[i] == 'short':
                        open_profit -= x * (self.current_data[i].close - self.entry_price[i])
            self.equity_log.loc[ind, 'close_balance'] = close_balance
            self.equity_log.loc[ind, 'open_profit'] = open_profit
            last_equity = open_profit + close_balance
            self.equity_log.loc[ind, 'equity'] = last_equity


    def getPercentDrawDown(self):
        peak = 0
        for index, e in self.equity_log.iterrows():
            if peak < e.equity:
                peak = e.equity
            current_draw_down = (peak - e.equity) / peak
            if current_draw_down > self.max_draw_down:
                self.max_draw_down = current_draw_down

    def getICAGR(self):
        length = len(self.equity_log)
        ratio = self.equity_log.loc[length-1, 'equity'] / self.equity_log.loc[0, 'equity']
        start_date = datetime.datetime.strptime(str(int(self.equity_log.loc[0, 'date'])), '%Y%m%d')
        end_date = datetime.datetime.strptime(str(int(self.equity_log.loc[length - 1, 'date'])), '%Y%m%d')
        d = end_date - start_date
        years = d.days / 365.25
        try:
            self.icagr = round(math.log(ratio) / years, 5)
        except Exception as ex:
            print('ratio', ratio)

    def getBliss(self):
        self.bliss = self.icagr / self.max_draw_down

    def mainFunc(self):
        self.setData()
        self.generateTradeLog()
        self.onGoningTrade()
        self.getPercentDrawDown()
        self.getICAGR()
        self.getBliss()


start = datetime.datetime.now()
# filenames = ['SP2_B2.CSV', 'JY_B.CSV', 'GC2_B.CSV', 'ED_B.CSV', 'CT2_B.CSV', 'CL2_B.CSV', 'BP_B.CSV', 'US_B.CSV', 'SB2_B.CSV', 'S2_B.CSV', 'PL2_B.CSV', 'LC_B.CSV']
filenames = ['AD_B.CSV', 'BO2_B.CSV', 'BP_B.CSV', 'C2_B.CSV', 'CD_B.CSV', 'CL2_B.CSV', 'CT2_B.CSV', 'CU_B.CSV',
             'DX2_B.CSV', 'ED_B.CSV', 'FC_B.CSV', 'FF_B.CSV', 'FV_B.CSV', 'GC2_B.CSV', 'HG2_B.CSV', 'HO2_B.CSV',
             'JY_B.CSV', 'LC_B.CSV', 'LH_B.CSV', 'NE_B.CSV', 'NG2_B.CSV', 'NK_B.CSV', 'O2_B.CSV', 'PA2_B.CSV',
             'PL2_B.CSV', 'RB2_B.CSV', 'RR2_B.CSV', 'RU_B.CSV', 'S2_B.CSV', 'SB2_B.CSV', 'SF_B.CSV', 'SI2_B.CSV',
             'SP2_B.CSV', 'US_B.CSV', 'W2_B.CSV']
# filenames = ['BP_B.CSV', 'CD_B.CSV']
for num, f in enumerate(filenames):
    filenames[num] = './in_data/reorganize/' + f

ea = BOT(filenames, config.Setting)
ea.mainFunc()
# ea.profitSum.to_csv('./out_data/profitSum.csv')
ea.trade_log.to_csv('./out_data/tradeLogBOT.csv')
ea.equity_log.to_csv('./out_data/equityLogBOT.csv')
end = datetime.datetime.now()
print(ea.equity_log)
print('ICAGR:' + str(ea.icagr) + ', PDD：' + str(ea.max_draw_down) + ', bliss:' + str(ea.bliss) + ', run time:' + str(
    end - start))
#     msg += 'fast:20, slow:'+str(slow)+', ICAGR:'+str(ea.icagr)+', PDD：'+str(ea.max_draw_down)+', bliss:'+str(ea.bliss)+', run time'+str(end - start)+"\n"
# print(msg)
