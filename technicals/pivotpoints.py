from pyalgotrade import technical
from pyalgotrade.dataseries import bards, SequenceDataSeries
import datetime
import numpy as np
import pandas as pd
import collections


class PivotPointsEventWindow(technical.EventWindow):
    def __init__(self, windowSize, period, frequency, useTypicalPrice):
        """
        This class is required by the library. Pivot levels are computed and stored in self.pp
        """
        super(PivotPointsEventWindow, self).__init__(windowSize, dtype=object)
        assert isinstance(frequency, str)

        self._useTypicalPrice = useTypicalPrice
        self.pp = collections.OrderedDict()
        self.conversion = {'high': 'max', 'low': 'min', 'close': 'last'}  # needed for resampling
        self.period = str(period) + frequency
        self.time_increment = {PivotPointsPeriod.converter[frequency]: period}
        self.previous_values = None

    def _insert_into_dict(self, date, max, min, close):
        """
        Inserts high, low, close into the dictionary, with the key being the date.
        :param date: datetime
        :param max: float, max price during period
        :param min: float, min price during period
        :param close: float
        :return:
        """
        if max > self.pp[date].get('high', -np.inf):
            self.pp[date]['high'] = max
        if min < self.pp[date].get('low', np.inf):
            self.pp[date]['low'] = min
        self.pp[date]['close'] = close

    def _compute_and_insert_pp(self, values):
        """
        Computes the pivot points for the next timeframe and inserts the levels into self.pp
        """

        # Data points of this day should be used to calculate the pivot points of the next day
        if any(values != self.previous_values):  # in case theres a lot of repeated data
            date = values.name + datetime.timedelta(**self.time_increment)
            if self.pp.get(date) is None:  # Pivot for this date doesnt exist
                self.pp[date] = {}  # Initialise

            # overwrite close, high, low for the current date
            self._insert_into_dict(date, values.high, values.low, values.close)
            # update the pivot levels
            self.pp[date].update(
                calculatePivotPoints(self.pp[date]['high'], self.pp[date]['low'], self.pp[date]['close']))
            # only needs to be set if values changed
            self.previous_values = values

    def onNewValue(self, dateTime, value):
        """
        Required by the library as an entry point. The values returned here are what the user gets.
        :param dateTime:
        :param value:
        :return: None or dict. These will form a part of an array of values, e.g. [None, None, OrderedDict, ...]
        """
        super(PivotPointsEventWindow, self).onNewValue(dateTime, value)
        return self.getValue()

    def getValue(self):
        """
        "main" process. If enough values are present, values are put in a dataframe and resampled for the correct period
        that the user specified. For all the resampled values (inside the window), the pivot points are computed and
        a dict with the levels is returned.
        :return:  None or dict
        """
        if self.windowFull():
            values = list(map(lambda x: [x.getDateTime(), x.getHigh(), x.getLow(), x.getClose()], self.getValues()))
            values = pd.DataFrame(values, columns=['date', 'high', 'low', 'close'])
            values = values.resample(self.period, on='date', how=self.conversion)

            for i in range(len(values)):
                self._compute_and_insert_pp(values.iloc[i])
            return self.pp
        else:
            return None


class PivotPointsPeriod():
    """
    Helper class defining the possible pivot point periods. When passing the period as an argument, one of these
    should be used.
    """
    min = 'Min'
    hourly = 'H'
    daily = 'D'
    weekly = 'W'
    monthy = 'M'

    converter = {'Min': 'minutes', 'H': 'hours', 'D': 'days', 'W': 'weeks', 'M': 'months'}


class PivotPointsEventBased(technical.EventBasedFilter):
    def __init__(self, dataSeries, windowSize, period_number, frequency, useTypicalPrice=False, maxLen=None):
        """
        :param dataSeries: dataSeries being used
        :param windowSize: number of data points to use to calculate the indicator.
        :param period_number: int object specifying the number of periods that the pivot points should be calculated on
        :param frequency: PivotPointsPeriod value
        :param useTypicalPrice: bool
        :param maxLen: The maximum number of values to hold.
        Once a bounded length is full, when new items are added, a corresponding number of items are discarded from the
        opposite end. If None then dataseries.DEFAULT_MAX_LEN is used.

        Example call: pivotpoints.PivotPointsEventBased(feed[instrument], vwapWindowSize, 1, pivotpoints.PivotPointsPeriod.daily)

        The only difference between PivotPointsEventBased and PivotPointsSequenceBased is the way the data is
        presented and the different backend process:

        The difference between this class and PivotPointsSequenceBased is that the values for all levels are returned
        in an array of ordered dictionaries in this case, wheres only the dates and values of the individual levels
        are returned in PivotPointsSequenceBased.

        Also, PivotPointsEventBased contains a dict for EVERY loop, making it less efficient than PivotPointsSequenceBased.
        This means that if you want daily pp and the data is in minutes, many values will be the same.

        PivotPointsEventBased: self.pp._SequenceDataSeries__values[date] --> {'high': 1.3122, 'low': 1.3047, 'close': 1.3091999999999999, 'PP': 1.3087, 'R1': 1.3127, 'R2': 1.3161999999999998, 'R3': 1.3202, 'S1': 1.3051999999999999, 'S2': 1.3011999999999999, 'S3': 1.2976999999999999}
        PivotPointsSequenceBased: self.pp.pivot_levels --> {'PP': SequenceDataSeries, 'R1': ..., ...}
                                  self._pp.pivot_levels['PP']._SequenceDataSeries__dateTimes._ListDeque__values --> [datetime, ..., datetime]
                                  self._pp.pivot_levels['PP']._SequenceDataSeries__values._ListDeque__values --> [float, ..., float]

        Another difference is that in PivotPointsEventBased, the first windowSize values will be None, whereas
        PivotPointsSequenceBased will start with a valid value since the None-s aren't saved.
        """
        assert isinstance(dataSeries, bards.BarDataSeries), \
            "dataSeries must be a dataseries.bards.BarDataSeries instance"
        assert frequency in PivotPointsPeriod.__dict__.values(), \
            "frequency must be one of the static variables defined in pivotpoints.PivotPointsPeriod, e.g. PivotPointsPeriod.daily"

        super(PivotPointsEventBased, self).__init__(dataSeries,
                                                    PivotPointsEventWindow(windowSize, period_number, frequency,
                                                                           useTypicalPrice),
                                                    maxLen)

    def getCurrentLevels(self):
        """
        Returns the currently computed levels for the user specified period.
        :return:
        """
        if len(self._EventBasedFilter__eventWindow.pp) != 0:
            return (list(self._EventBasedFilter__eventWindow.pp.keys()),
                    list(self._EventBasedFilter__eventWindow.pp.values()))
        else:
            return (None, None)

    def getAllDatetimes(self):
        """
        Returns all the datetimes for every loop!
        :return: list
        """
        return self._SequenceDataSeries__dateTimes._ListDeque__values

    def getAllLevels(self):
        """
        Returns all the levels for every loop!
        :return: list
        """
        return self._SequenceDataSeries__values._ListDeque__values


class PivotPointsSequenceBased(SequenceDataSeries):
    def __init__(self, dataSeries, windowSize, period, frequency, useTypicalPrice=False, maxLen=None):
        """
        :param dataSeries: dataSeries being used
        :param windowSize: number of data points to use to calculate the indicator.
        :param period_number: int object specifying the number of periods that the pivot points should be calculated on
        :param frequency: PivotPointsPeriod value
        :param useTypicalPrice: bool
        :param maxLen: The maximum number of values to hold.

        Example call: pivotpoints.PivotPointsSequenceBased(feed[instrument], vwapWindowSize, 1, pivotpoints.PivotPointsPeriod.daily)

        The only difference between PivotPointsEventBased and PivotPointsSequenceBased is the way the data is
        presented and the different backend process.
        """
        super(PivotPointsSequenceBased, self).__init__(maxLen)
        assert isinstance(frequency, str)
        self._ppWindow = PivotPointsEventWindow(windowSize, period, frequency, useTypicalPrice)

        self.levels = ['PP', 'R1', 'R2', 'R3', 'S1', 'S2', 'S3']
        self.pivot_levels = PivotPointsSequenceBased.__init_pivot_levels(self.levels)
        dataSeries.getNewValueEvent().subscribe(self.__onNewValue)

    @staticmethod
    def __init_pivot_levels(levels, maxLen=None):
        return {l: SequenceDataSeries(maxLen) for l in levels}

    def __onNewValue(self, dataSeries, dateTime, value):
        pp = self._ppWindow.onNewValue(dateTime, value)
        if pp:
            # Get the last item
            _, data = list(pp.items())[-1]
            # Append the values calculated for the next periods pivot point to the current date
            self.__append_data(dateTime + datetime.timedelta(**self._ppWindow.time_increment), data)

    def __append_data(self, date, data):
        ''' Append the data to the corresponding series'''
        for l in self.levels:
            self.pivot_levels[l].appendWithDateTime(date, data[l])

    def getPivotPointLevel(self, level):
        ''' Returns the SequenceDataSeries datetime and values arrays as a tuple '''
        return (self.pivot_levels[level]._SequenceDataSeries__dateTimes._ListDeque__values,
                self.pivot_levels[level]._SequenceDataSeries__values._ListDeque__values)

    def getLastPivotLevel(self, level):
        """
        Gets the last pivot value
        :param level: One of self.levels
        :return: tuple(datetime, float)
        """
        dates = self.pivot_levels[level]._SequenceDataSeries__dateTimes._ListDeque__values
        values = self.pivot_levels[level]._SequenceDataSeries__values._ListDeque__values
        return (dates[-1], values[-1]) if len(values) > 0 else (dates, values)


def calculatePivotPoints(h, l, c):
    """
    Compute Pivot Points for just one level
    """
    pp = (h + l + c) / 3
    r1 = 2 * pp - l
    s1 = 2 * pp - h
    r2 = pp + h - l
    s2 = pp - h + l
    r3 = h + 2 * (pp - l)
    s3 = l - 2 * (h - pp)
    return dict(PP=pp, R1=r1, R2=r2, R3=r3, S1=s1, S2=s2, S3=s3)
