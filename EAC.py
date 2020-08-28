# -*- coding: UTF-8 -*-
import datetime
import pandas as pd
import math


class EA(object):
    def __init__(self, filenames, setting):
        self.files = filenames
        self.fast = setting['fast']
        self.slow = setting['slow']
        self.init_equity = setting['equity']
        self.heat = setting['heat']
        self.atr_period = setting['atr_period']
        self.sl_atr_period = setting['sl_atr_period']
        self.atr_multiplier = setting['atr_multiplier']
        self.stop_loss_days = setting['stop_loss_days']
        self.count = setting['count']
        self.icagr = 0.00
        self.max_draw_down = 0.00
        self.bliss = 0.00

    def initTmp(self):
        # 作用为全局临时变量
        self.current_position = []
        self.current_price = []
        self.last_date = []
        self.last_price = []
        self.entry_price = []
        for num in range(0, self.count, 1):
            self.current_position.append(0)
            self.last_date.append(0)
            self.current_price.append(0.00)
            self.last_price.append(0.00)
            self.entry_price.append(0.00)

    def setData(self):
        self.data = []
        self.trade_info = []
        self.data_d = []
        for i, f in enumerate(self.files):
            self.data.append(pd.read_csv(f, names=['date', 'open', 'high', 'low', 'close', 'volume', 'open_volume'], usecols=[0, 1, 2, 3, 4, 5, 6]))
            self.data_d.append(self.data[i].set_index('date'))  #以date为index，加快运算速度
            self.data[i]['fast_lag'] = self.getLag(self.data[i].close, self.fast)
            self.data[i]['slow_lag'] = self.getLag(self.data[i].close, self.slow)
            self.data[i]['atr'] = self.getATR(i, self.atr_period)
            self.calculateTrade(i)

    def getLag(self, prices, time_const):
        lag = []
        last_lag = prices[0]
        for d in prices:
            current_lag = float(last_lag + (d - last_lag)*2 / (time_const + 1))
            lag.append(current_lag)
            last_lag = current_lag
        return lag

    def calculateTrade(self, ind):
        trade = []
        for index, d in self.data[ind].iterrows():
            if index == 25:
                last_lag_diff = d.fast_lag - d.slow_lag
            elif index > 25:
                current_lag_diff = d.fast_lag - d.slow_lag
                if (last_lag_diff >= 0 and current_lag_diff < 0 and len(trade) > 0):  # sell
                    if index < len(self.data[ind]) - 1:
                        trade.append([int(self.data[ind].loc[index + 1, 'date']),
                                      float((self.data[ind].loc[index + 1].open + self.data[ind].loc[index + 1, 'low']) / 2), 'Exit'])
                elif (last_lag_diff <= 0 and current_lag_diff > 0):  # buy
                    if index == len(self.data[ind]) - 1:  # 最后一天触发buy
                        trade.append([int(self.data[ind].loc[index, 'date']),
                             float((self.data[ind].loc[index].open + self.data[ind].loc[index, 'high']) / 2), 'Entry'])
                    else:
                        trade.append([int(self.data[ind].loc[index + 1, 'date']),
                                      float((self.data[ind].loc[index + 1].open + self.data[ind].loc[index + 1, 'high']) / 2), 'Entry'])
                last_lag_diff = current_lag_diff
            if index == len(self.data[ind]) - 1 and len(trade) >= 1 and trade[-1][2] == 'Entry':
                trade.append([int(d.date), float(d.close), 'Exit'])
        self.trade_info.append(pd.DataFrame(columns=['date', 'price', 'note'], data=trade))
        self.trade_info[ind]['instru'] = ind
        self.trailingStopLoss(ind)
        #self.stopLossInTrade(ind)

    def stopLossInTrade(self, index):
        for ind, t in self.trade_info[index].iterrows():
            if t.note == 'Entry':
                tmp_index = self.data[index].loc[self.data[index].date == t.date].index.values
                tmp_index = tmp_index[0]
                # 过了一定天数(交易日)没有盈利,且趋势没有显示转变(即尚未卖出)，次日平仓。以下计算方式必须建立在trade里面Entry和Exit交替出现的基础上
                if tmp_index + self.stop_loss_days <= len(self.data[index]) \
                   and t.price > self.data[index].loc[tmp_index + self.stop_loss_days, 'close'] \
                   and self.trade_info[index].loc[ind + 1, 'date'] > self.data[index].loc[tmp_index + self.stop_loss_days, 'date']:
                    self.trade_info[index].loc[ind + 1, 'date'] = self.data[index].loc[tmp_index + 1, 'date']
                    self.trade_info[index].loc[ind + 1, 'price'] = float((self.data[index].loc[tmp_index + 1].open + self.data[index].loc[tmp_index + 1, 'low']) / 2)

    def trailingStopLoss(self, index):
        #self.data[index]['sl_atr'] = self.getATR(index, self.sl_atr_period)
        ind_t = 0
        while ind_t < len(self.trade_info[index]) - 1:
            price_high = 0
            trailing_stop = 0
            entry = self.trade_info[index].iloc[ind_t]
            exit = self.trade_info[index].iloc[ind_t + 1]
            start = self.data[index][self.data[index].date == entry.date].index.values
            end = self.data[index][self.data[index].date == exit.date].index.values
            data_in_trade = self.data[index].loc[start[0]:end[0]]
            for ind, d in data_in_trade.iterrows():
                if d.close <= trailing_stop and ind < len(self.data[index]) - 1:
                    # print('instru:', index, 'no:', ind_t, 'price_high:', price_high, 'trailing_stop:', trailing_stop, 'close:', d.close, 'date:', self.data[index].loc[ind + 1, 'date'])
                    self.trade_info[index].loc[ind_t + 1, 'date'] = self.data[index].loc[ind + 1, 'date']
                    self.trade_info[index].loc[ind_t + 1, 'price'] = float((self.data[index].loc[ind + 1].open + self.data[index].loc[ind + 1, 'low']) / 2)
                    break
                if price_high < d.close:
                    price_high = d.close
                if trailing_stop < price_high - 3 * d.atr:
                    trailing_stop = price_high - 3 * d.atr
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
        self.trade_log['left_equity'] = self.init_equity
        self.trade_log['unit'] = 0

    def getPositionAndProfit(self):
        self.initTmp()
        left_equity = self.init_equity  # 当前不参与交易的资金
        profit = []
        for index, t in self.trade_log.iterrows():
            if t.note == 'Entry':
                current_atr_index = self.data[t.instru][self.data[t.instru].date == t.date].index.values
                last_atr = self.data[t.instru].iloc[current_atr_index[0] - 1].atr
                # 当前equity计算(此时按前一天的equity计算)
                equity = left_equity
                for i, x in enumerate(self.current_position):
                    if x != 0:
                        try:
                            d_index = self.data[i][self.data[i].date == t.date].index.values
                            equity += x * self.data[i].iloc[d_index[0] - 1].close
                        except Exception as e:
                            # 当拥有交易标的，但该日期没有价格信息，往前找最近的日子
                            for ind, d in self.data[i].iterrows():
                                if d.date >= t.date:
                                    break
                                tmp_index = ind
                            print('trade date miss', self.data[i].loc[tmp_index, 'date'])
                            equity += x * self.data[i].loc[tmp_index, 'close']
                tmp_size = equity * self.heat / (last_atr * self.atr_multiplier)
                unit = int(tmp_size / 250)
                unit = unit + 1 if tmp_size % 250 > 125 else unit
                # print('date', t.date, 'equity:', equity, 'last_atr:', last_atr, 'tmp_size:', tmp_size, 'unit:', unit)
                self.current_position[t.instru] = unit * 250
                left_equity = left_equity - self.current_position[t.instru] * t.price
                self.last_date[t.instru] = t.date
                self.last_price[t.instru] = t.price
                self.trade_log.loc[index, 'unit'] = self.current_position[t.instru]
            elif t.note == 'Exit':
                profit.append([self.current_position[t.instru], self.last_date[t.instru], self.last_price[t.instru], t.date, t.price,
                               float(self.current_position[t.instru] * (t.price - self.last_price[t.instru])), t.instru])
                left_equity = left_equity + self.current_position[t.instru] * t.price
                self.current_position[t.instru] = 0
                self.last_price[t.instru] = 0
                self.last_date[t.instru] = 0
                self.trade_log.loc[index, 'unit'] = 0
            self.trade_log.loc[index, 'left_equity'] = left_equity
        self.profit = pd.DataFrame(columns=['unit', 'entry_date', 'entry_price', 'exit_date', 'exit_price', 'profit', 'instru'], data=profit)

    def profitSum(self):
        profitSum = []
        self.totalProfit = 0
        for num in range(0, self.count, 1):
            profitSum.append([self.files[num], 0])
        for index, p in self.profit.iterrows():
            profitSum[int(p.instru)][1] = profitSum[int(p.instru)][1] + p.profit
            self.totalProfit = self.totalProfit + p.profit
        for num in range(0, self.count, 1):
            profitSum[num][1] = round(profitSum[num][1], 4)
            profitSum[num].append(round(profitSum[num][1] / self.totalProfit, 4))
        self.profitSum = pd.DataFrame(columns=['file', 'profit', 'rate'], data=profitSum)

    def getMergeDate(self):
        date_set = set([])
        for d in self.data:
            temp_set = set(d.date)
            date_set = date_set | temp_set
        date_list = list(date_set)
        date_list.sort()
        return date_list

    def getEquityLog(self):
        self.initTmp()
        self.equity_log = pd.DataFrame(columns=['date'], data=self.getMergeDate())
        self.equity_log['close_balance'] = self.init_equity
        self.equity_log['open_profit'] = 0.00
        self.equity_log['equity'] = self.init_equity
        left_equity = self.init_equity
        close_balance = self.init_equity
        # 在equity_log 和 trade_log 这两个循环里面，预设两边最后一个date是相同的，如果有不同的情况需要修改
        index_t = 0
        current_trade = self.trade_log.iloc[index_t]
        for index, d in self.equity_log.iterrows():
            while d.date == current_trade.date and index_t < len(self.trade_log):
                left_equity = current_trade.left_equity
                self.current_position[current_trade.instru] = current_trade.unit
                if current_trade.note == 'Entry':
                    self.entry_price[current_trade.instru] = current_trade.price
                if current_trade.note == 'Exit':
                    #close_balance = close_balance + self.profit[current_trade.date == self.profit.exit_date]['profit'].iloc[0]
                    close_balance = close_balance + self.current_position[current_trade.instru] * (current_trade.price - self.entry_price[current_trade.instru])
                    self.entry_price[current_trade.instru] = 0
                current_trade = self.trade_log.iloc[index_t]
                index_t = index_t + 1

            if d.date <= current_trade.date:
                equity = left_equity
                for i, x in enumerate(self.current_position):
                    if x != 0:
                        try:
                            self.current_price[i] = self.data_d[i].loc[d.date, 'close']
                        except Exception as ex:
                            print('equity date miss', d.date)
                        equity += x * self.current_price[i]
                self.equity_log.loc[index, 'equity'] = equity
                self.equity_log.loc[index, 'close_balance'] = close_balance
                self.equity_log.loc[index, 'open_profit'] = equity - close_balance

    def getEquityLogInOpenprofit(self):
        self.initTmp()
        self.equity_log = pd.DataFrame(columns=['date'], data=self.getMergeDate())
        self.equity_log['close_balance'] = self.init_equity
        self.equity_log['open_profit'] = 0.00
        self.equity_log['equity'] = self.init_equity
        self.after_profit = []
        close_balance = self.init_equity
        index_t = 0
        # 在equity_log 和 trade_log 这两个循环里面，预设两边最后一个date是相同的，如果有不同的情况需要修改
        current_trade = self.trade_log.iloc[index_t]
        for index, d in self.equity_log.iterrows():
            while d.date == current_trade.date and index_t < len(self.trade_log):
                if current_trade.note == 'Entry':
                    self.entry_price[current_trade.instru] = current_trade.price
                if current_trade.note == 'Exit':
                    close_balance = close_balance + self.current_position[current_trade.instru] * (current_trade.price - self.entry_price[current_trade.instru])
                    self.entry_price[current_trade.instru] = 0
                self.current_position[current_trade.instru] = current_trade.unit
                current_trade = self.trade_log.iloc[index_t]
                index_t = index_t + 1

            if d.date <= current_trade.date:
                open_profit = 0
                for i, x in enumerate(self.current_position):
                    if x != 0:
                        try:
                            self.current_price[i] = self.data_d[i].loc[d.date, 'close']
                        except Exception as ex:
                            print('equity date miss', d.date)
                        open_profit += x * (self.current_price[i] - self.entry_price[i])
                self.equity_log.loc[index, 'close_balance'] = close_balance
                self.equity_log.loc[index, 'open_profit'] = open_profit
                self.equity_log.loc[index, 'equity'] = open_profit + close_balance

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
        ratio = self.equity_log.loc[length - 1, 'equity'] / self.equity_log.loc[0, 'equity']
        start_date = datetime.datetime.strptime(str(self.equity_log.loc[0, 'date']), '%Y%m%d')
        end_date = datetime.datetime.strptime(str(self.equity_log.loc[length - 1, 'date']), '%Y%m%d')
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
        self.getPositionAndProfit()
        #self.profitSum()
        #self.getEquityLog()
        self.getEquityLogInOpenprofit()
        self.getICAGR()
        self.getPercentDrawDown()
        self.getBliss()

# msg = ''
# for sl_days in range(30, 91, 10):
start = datetime.datetime.now()
#filenames = ['SP2_B2.CSV', 'JY_B.CSV', 'GC2_B.CSV', 'ED_B.CSV', 'CT2_B.CSV', 'CL2_B.CSV', 'BP_B.CSV', 'US_B.CSV', 'SB2_B.CSV', 'S2_B.CSV', 'PL2_B.CSV', 'LC_B.CSV']
# filenames = ['AD_B.CSV', 'BO2_B.CSV', 'BP_B.CSV', 'C2_B.CSV', 'CD_B.CSV', 'CL2_B.CSV', 'CT2_B.CSV', 'CU_B.CSV', 'DJ_B.CSV', 'DX2_B.CSV',
#              'ED_B.CSV', 'FC_B.CSV', 'GC2_B.CSV', 'HG2_B.CSV', 'HO2_B.CSV', 'JY_B.CSV', 'LC_B.CSV', 'LH_B.CSV', 'ND_B.CSV', 'NE_B.CSV',
#              'NG2_B.CSV', 'O2_B.CSV', 'PA2_B.CSV', 'PL2_B.CSV', 'RB2_B.CSV', 'RR2_B.CSV', 'RU_B.CSV',  'SB2_B.CSV', 'SF_B.CSV',
#              'SI2_B.CSV', 'SP2_B.CSV', 'T1U_B.CSV', 'US_B.CSV', 'W2_B.CSV', 'S2_B.CSV'] #'SM2_B.CSV',   'S2_B.CSV', 价格为负数先不管
filenames = ['AD_B.CSV', 'BO2_B.CSV']
for i, f in enumerate(filenames):
    filenames[i] = './in_data/new36/' + f  # new36/

setting = {
    'count': 35,
    'fast': 10,
    'slow': 100,
    'equity': 2000000.00,
    'heat': 0.005,
    'atr_period': 100,
    'sl_atr_period': 100,
    'atr_multiplier': 5,
    'stop_loss_days': 60
}
ea = EA(filenames, setting)
ea.mainFunc()
#ea.profitSum.to_csv('./out_data/profitSum.csv')
#ea.trade_log.to_csv('./out_data/tradeLog36.csv')
ea.equity_log.to_csv('./out_data/equityLog34.csv')
end = datetime.datetime.now()
print('ICAGR:'+str(ea.icagr)+', PDD：'+str(ea.max_draw_down)+', bliss:'+str(ea.bliss)+', run time:'+str(end - start))
#     msg += 'fast:20, slow:'+str(slow)+', ICAGR:'+str(ea.icagr)+', PDD：'+str(ea.max_draw_down)+', bliss:'+str(ea.bliss)+', run time'+str(end - start)+"\n"
# print(msg)
