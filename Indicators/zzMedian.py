from collections import deque
import datetime
import backtrader.feeds as btfeeds
import backtrader as bt
import numpy as np

data = btfeeds.GenericCSVData(
    fromdate=datetime.datetime(2021, 1, 1),
    dataname='mydata.csv',
    todate=datetime.datetime(2021, 4, 7),
    nullvalue=0.0,
    dtformat=('%Y-%m-%d'),
    datetime=0,
    high=1,
    low=2,
    open=3,
    close=4,
    volume=5,
    openinterest=-1
)

__all__ = ['ZigZag', 'ZigZagLen', ]


class ZigZagLen(bt.Indicator):
    params = (
        ## ZigZag inputs
        ('retrace', 0.05),  # in percent
        ('minbars', 14),  # number of bars to skip after the trend change
        ##

        # ZigZagLen inputs
        ('full_init', True),  #
        ('period', 6 * 90,),  # 6*90  # positive number for rolling series, -1 for expanding series
        ('output', 'median'),  # median or mean
        ('del_outliers', True),

        ('alpha', 0.05),  # exponential smoothing input
    )

    lines = ('combined', 'bull', 'bear')

    def __init__(self):
        self.zigzag = ZigZag(retrace=self.p.retrace,
                             minbars=self.p.minbars, )

        assert self.p.output in ['median', 'mean']

        if self.p.output == 'median':
            self.func = np.median
        elif self.p.output == 'mean':
            self.func = np.mean

        self.stored_listlen = 0

        if self.p.full_init:
            assert self.p.period > 0, 'when full_init is enabled, we need a minimum period'
            self.addminperiod(self.p.period)

    def next(self):
        zz = self.zigzag
        l = self.l
        llist = {l.combined: ['bull', 'bear'],
                 l.bull    : ['bull'],
                 l.bear    : ['bear'], }

        # # No new values. Copying previous values instead of repeating calculations
        if len(zz.lenlist) < self.stored_listlen:
            for line in llist.keys():
                line[0] = line[-1]
            return

        self.stored_listlen = len(zz.lenlist)

        # Do we have at least something to work with?
        if len(zz.lenlist) >= 8:

            if self.p.del_outliers:
                q1 = np.percentile(zz.lenlist, 25)
                q3 = np.percentile(zz.lenlist, 75)
                iqr = q3 - q1
                upperlim = q3 + 1.5 * iqr
                lowerlim = q1 - 1.5 * iqr
            else:
                upperlim = float('inf')
                lowerlim = 0

            lenlist = list(reversed(zz.lenlist))
            if self.p.period > 0:  # Rolling series

                if sum(lenlist) > self.p.period:
                    # finding index of last value in our moving series
                    cumlst = np.cumsum(lenlist)
                    idx = np.where(cumlst > self.p.period)[0][0]
                    lenlist = lenlist[:idx]

            # Getting the length of current move
            last_len = InfoInt(zz.since_last_pivot)
            last_len.bias = 'bear' if lenlist[0].bias != 'bear' else 'bull'
            lenlist.append(last_len)

            for line, bias in llist.items():
                filter_lst = [v for v in lenlist if lowerlim < v < upperlim
                              and v.bias in bias]

                output = self.func(filter_lst)
                if np.isnan(line[-1]):
                    line[0] = output
                else:
                    alpha = self.p.alpha
                    line[0] = line[-1] * (1 - alpha) + output * alpha


# inheriting allows us to add variables to an int
class InfoInt(int):
    pass


class ZigZag(bt.Indicator):
    '''
      ZigZag indicator.
    '''
    lines = (
        'trend',
        'last_high',
        'last_low',
        'zigzag',
    )

    plotinfo = dict(
        subplot=False,
        plotlinelabels=True, plotlinevalues=True, plotvaluetags=True,
    )

    plotlines = dict(
        trend=dict(_plotskip=True),
        last_high=dict(color='green', ls='-', _plotskip=True),
        last_low=dict(color='black', ls='-', _plotskip=True),
        zigzag=dict(_name='zigzag', color='blue', ls='-', _skipnan=True),
    )

    params = (
        ('retrace', 0.05),  # in percent
        ('minbars', 14),  # number of bars to skip after the trend change
    )

    def __init__(self):
        super(ZigZag, self).__init__()

        self.addminperiod(self.p.minbars)

        assert self.p.retrace > 0, 'Retracement should be above zero.'
        assert self.p.minbars >= 0, 'Minimal bars should be >= zero.'

        self.retrace_thresh = self.data.close * self.p.retrace / 100
        self.minbars = self.p.minbars
        self.count_bars = 0
        self.last_pivots = deque([0, 0], maxlen=2)
        self.last_pivot_t = 0
        self.since_last_pivot = 0
        self.lenlist = []

        self.stored_datalen = 0

    def prenext(self):
        self.l.trend[0] = 0
        self.l.last_high[0] = self.data.high[0]
        self.l.last_low[0] = self.data.low[0]
        self.l.zigzag[0] = (self.data.high[0] + self.data.low[0]) / 2

    def next(self):

        # No new candle. Got called due to resampling
        if len(self.data) == self.stored_datalen:
            return
        self.stored_datalen = len(self.data)

        curr_idx = len(self.data)
        self.retrace_thresh = self.data.close[0] * self.p.retrace / 100
        self.since_last_pivot = curr_idx - self.last_pivot_t
        self.l.trend[0] = self.l.trend[-1]
        self.l.last_high[0] = self.l.last_high[-1]
        self.l.last_low[0] = self.l.last_low[-1]
        self.l.zigzag[0] = float('nan')

        # Initialize trend
        if self.l.trend[-1] == 0:
            # If current candle has higher low and higher high
            if self.l.last_low[0] < self.data.low[0] and self.l.last_high[0] < self.data.high[0]:
                self.l.trend[0] = 1
                self.l.last_high[0] = self.data.high[0]
                self.last_pivot_t = curr_idx
            # If current candle has lower low and lower high
            elif self.l.last_low[0] > self.data.low[0] and self.l.last_high[0] > self.data.high[0]:
                self.l.trend[0] = -1
                self.l.last_low[0] = self.data.low[0]
                self.last_pivot_t = curr_idx

        # Up trend
        elif self.l.trend[-1] == 1:
            # if higher high, move pivot location to current high
            if self.data.high[0] > self.l.last_high[-1]:
                self.l.last_high[0] = self.data.high[0]
                self.count_bars = self.minbars
                self.last_pivot_t = curr_idx

            # elif at least p.minbars since last bull swing and currently in a retrace -> Switch Bearish
            elif self.count_bars <= 0 and self.l.last_high[0] - self.data.low[0] > self.retrace_thresh \
                    and self.data.high[0] < self.l.last_high[0]:
                self.switch_to_bear(curr_idx)

            # elif bearish close
            elif self.count_bars < self.minbars and self.data.close[0] < self.l.last_low[0]:
                self.switch_to_bear(curr_idx)

        # Down trend
        elif self.l.trend[-1] == -1:
            # if lower low, move pivot location to current low
            if self.data.low[0] < self.l.last_low[-1]:
                self.l.last_low[0] = self.data.low[0]
                self.count_bars = self.minbars
                self.last_pivot_t = curr_idx

            # elif we had an established bear swing and currently in a retrace -> Switch Bullish
            elif self.count_bars <= 0 and self.data.high[0] - self.l.last_low[0] > self.retrace_thresh and \
                    self.data.low[0] > self.l.last_low[0]:
                self.switch_to_bull(curr_idx)
            # elif bullish close
            elif self.count_bars < self.minbars and self.data.close[0] > self.l.last_high[-1]:
                self.switch_to_bull(curr_idx)

        # Decrease minbars counter
        self.count_bars -= 1

    def switch_to_bear(self, idx):
        self.l.trend[0] = -1
        self.count_bars = self.minbars
        self.l.last_low[0] = self.data.low[0]
        self.l.zigzag[-self.since_last_pivot] = self.l.last_high[0]
        self.last_pivot_t = idx

        self.record_idx(idx, 'bull', )

    def switch_to_bull(self, idx):
        self.l.trend[0] = 1
        self.count_bars = self.minbars
        self.l.last_high[0] = self.data.high[0]
        self.l.zigzag[-self.since_last_pivot] = self.l.last_low[0]
        self.last_pivot_t = idx

        self.record_idx(idx, 'bear', )

    def record_idx(self, idx, bias, ):
        self.last_pivots.append(idx)
        last_move_len = self.last_pivots[-1] - self.last_pivots[0]
        last_move_len = InfoInt(last_move_len)
        last_move_len.bias = bias

        self.lenlist.append(last_move_len)