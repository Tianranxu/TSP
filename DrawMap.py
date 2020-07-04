import matplotlib.pyplot as plt
import pandas as pd

prices = pd.read_csv('./out_data/out.csv', header=0)
trade = pd.read_csv('./out_data/trade.csv', header=0)

start_date = '2003-03-27'
end_date = '2003-07-22'

prices['date'] = pd.to_datetime(prices['date'], format='%Y%m%d', errors='ignore')
start = prices[(prices.date == start_date)].index.values
end = prices[prices.date == end_date].index.values
draw_data = prices.loc[start[0]:end[0]]
print(draw_data)
plt.plot(draw_data['date'], draw_data['close'])
plt.plot(draw_data['date'], draw_data['fast_lag'])
plt.plot(draw_data['date'], draw_data['slow_lag'])

trade['date'] = pd.to_datetime(trade['date'], format='%Y%m%d', errors='ignore')
trade_data = trade.loc[(trade['date'] >= start_date) & (trade['date'] <= end_date)]
buy = trade_data[trade_data.note == 'Entry']
sell = trade_data[trade_data.note == 'Exit']
if buy.iloc[:, 0].size > 0:
    plt.scatter(buy['date'], buy['price'], marker='^', c='r')
if sell.iloc[:, 0].size > 0:
    plt.scatter(sell['date'], sell['price'], marker='v', c='k')

# equity = pd.read_csv('./out_data/equityLog36.csv', header=0)
# plt.plot(equity['date'], equity['equity'])

plt.show()
