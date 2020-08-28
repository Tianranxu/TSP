# -*- coding: UTF-8 -*-
import pandas as pd


class Reorganize(object):
    def __init__(self, files, setting):
        self.files = files
        self.setting = setting
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
        for num in range(0, self.setting['count'], 1):
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
            self.data.append(pd.read_csv(f, names=['date', 'open', 'high', 'low', 'close', 'volume', 'open_volume'],
                                         usecols=[0, 1, 2, 3, 4, 5, 6]))
            self.data_d.append(self.data[i].set_index('date'))  # 以date为index，加快运算速度
            self.data[i]['fast_lag'] = self.getLag(self.data[i].close, self.setting['fast'])
            self.data[i]['slow_lag'] = self.getLag(self.data[i].close, self.setting['slow'])
            self.data[i]['atr'] = self.getATR(i, self.setting['atr_period'])
            self.getPeriodBreak(i)
            # self.calculateTrade(i)

    def getLag(self, prices, time_const):
        lag = []
        last_lag = prices[0]
        for d in prices:
            current_lag = float(last_lag + (d - last_lag) * 2 / (time_const + 1))
            lag.append(current_lag)
            last_lag = current_lag
        return lag

    def getATR(self, ind, period):
        ture_range = []
        last_close = self.data[ind].iloc[0].close
        for index, d in self.data[ind].iterrows():
            ture_range.append(max(d.high, last_close) - min(d.low, last_close))
            last_close = d.close
        return self.getLag(ture_range, period)

    # 计算过去n天内（不包括当天）的最高价与最低价，其中天数指交易日
    def getPeriodBreak(self, ind):
        for i, d in self.data[ind].iterrows():
            if i == 0:
                high1 = {'peak': [i, d.close], 'second': [-1, 0]}
                high2 = {'peak': [i, d.close], 'second': [-1, 0]}
                low1 = {'peak': [i, d.close], 'second': [-1, 0]}
                low2 = {'peak': [i, d.close], 'second': [-1, 0]}
                continue

            # 这里必须保证second的交易日必须在peak交易日后面，second目的在于保留peak之后的第二高价
            if d.close >= high1['peak'][1]:
                high1['peak'] = [i, d.close]
                high1['second'] = [-1, 0]
            elif high1['second'][0] == -1 or d.close >= high1['second'][1]:
                high1['second'] = [i, d.close]

            if i - high1['peak'][0] >= self.setting['break_limit_1']:  # 当最高价超过天数范围
                high1['peak'] = high1['second']
                high1['second'] = [-1, 0]
                if high1['peak'][0] != i:
                    # 往后面找第二高价
                    tmp_data = self.data[ind][high1['peak'][0]+1: i+1]
                    for c, td in tmp_data.iterrows():
                        if high1['second'][0] == -1 or td.close >= high1['second'][1]:
                            high1['second'] = [c, td.close]

            if d.close >= high2['peak'][1]:
                high2['peak'] = [i, d.close]
                high2['second'] = [-1, 0]
            elif high2['second'][0] == -1 or d.close >= high2['second'][1]:
                high2['second'] = [i, d.close]

            if i - high2['peak'][0] >= self.setting['break_limit_2']:  # 当最高价超过天数范围
                high2['peak'] = high2['second']
                high2['second'] = [-1, 0]
                if high2['peak'][0] != i:
                    # 往后面找第二高价
                    tmp_data = self.data[ind][high2['peak'][0]+1: i+1]
                    for c, td in tmp_data.iterrows():
                        if high2['second'][0] == -1 or td.close >= high2['second'][1]:
                            high2['second'] = [c, td.close]

            if d.close <= low1['peak'][1]:
                low1['peak'] = [i, d.close]
                low1['second'] = [-1, 0]
            elif low1['second'][0] == -1 or d.close <= low1['second'][1]:
                low1['second'] = [i, d.close]

            if i - low1['peak'][0] >= self.setting['break_limit_1']:  # 当最低价超过天数范围
                low1['peak'] = low1['second']
                low1['second'] = [-1, 0]
                if low1['peak'][0] != i:
                    # 往后面找第二低价
                    tmp_data = self.data[ind][low1['peak'][0] + 1: i + 1]
                    for c, td in tmp_data.iterrows():
                        if low1['second'][0] == -1 or td.close <= low1['second'][1]:
                            low1['second'] = [c, td.close]

            if d.close <= low2['peak'][1]:
                low2['peak'] = [i, d.close]
                low2['second'] = [-1, 0]
            elif low2['second'][0] == -1 or d.close <= low2['second'][1]:
                low2['second'] = [i, d.close]

            if i - low2['peak'][0] >= self.setting['break_limit_2']:  # 当最低价超过天数范围
                low2['peak'] = low2['second']
                low2['second'] = [-1, 0]
                if low2['peak'][0] != i:
                    # 往后面找第二低价
                    tmp_data = self.data[ind][low2['peak'][0] + 1: i + 1]
                    for c, td in tmp_data.iterrows():
                        if low2['second'][0] == -1 or td.close <= low2['second'][1]:
                            low2['second'] = [c, td.close]

            if i < len(self.data[ind])-1:
                self.data[ind].loc[i + 1, 'last_high1'] = high1['peak'][1]
                self.data[ind].loc[i + 1, 'last_high2'] = high2['peak'][1]
                self.data[ind].loc[i + 1, 'last_low1'] = low1['peak'][1]
                self.data[ind].loc[i + 1, 'last_low2'] = low2['peak'][1]

        # 直接算
        # for i, d in self.data[ind].iterrows():
        #     if i >= self.setting['break_limit_1']-1:
        #         tmp_data = self.data[ind][i-self.setting['break_limit_1']+1: i+1]
        #         print(tmp_data)
        #         thigh = 0
        #         for c, td in tmp_data.iterrows():
        #             if thigh < td.close:
        #                 thigh = td.close
        #         self.data[ind].loc[i+1, 'thigh'] = thigh


    def mainFunc(self, names):
        self.setData()
        for i, n in enumerate(names):
            self.data[i].to_csv('./in_data/reorganize/' + n)


# filenames = ['SP2_B2.CSV', 'JY_B.CSV', 'GC2_B.CSV', 'ED_B.CSV', 'CT2_B.CSV', 'CL2_B.CSV', 'BP_B.CSV', 'US_B.CSV', 'SB2_B.CSV', 'S2_B.CSV', 'PL2_B.CSV', 'LC_B.CSV']
filenames = ['AD_B.CSV', 'BO2_B.CSV', 'BP_B.CSV', 'C2_B.CSV', 'CD_B.CSV', 'CL2_B.CSV', 'CT2_B.CSV', 'CU_B.CSV', 'DX2_B.CSV', 'ED_B.CSV',
             'FC_B.CSV', 'FF_B.CSV', 'FV_B.CSV', 'GC2_B.CSV', 'HG2_B.CSV', 'HO2_B.CSV', 'JY_B.CSV', 'LC_B.CSV', 'LH_B.CSV', 'NE_B.CSV',
             'NG2_B.CSV', 'NK_B.CSV', 'O2_B.CSV', 'PA2_B.CSV', 'PL2_B.CSV', 'RB2_B.CSV', 'RR2_B.CSV', 'RU_B.CSV', 'S2_B.CSV', 'SB2_B.CSV',
             'SF_B.CSV', 'SI2_B.CSV', 'SP2_B.CSV',  'US_B.CSV', 'W2_B.CSV']
files = []
for num, f in enumerate(filenames):
    files.append('./in_data/new36/' + f)

setting = {
    'count': 1,
    'fast': 50,
    'slow': 100,
    'atr_period': 100,
    'sl_atr_period': 100,
    'atr_multiplier': 5,
    'stop_loss_days': 60,
    'break_limit_1': 50,
    'break_limit_2': 25,
}
re = Reorganize(files, setting)
re.mainFunc(filenames)
