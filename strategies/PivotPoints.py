from pyalgotrade import strategy
from pyalgotrade.technical import vwap
from technicals import pivotpoints

class PivotPointMomentum(strategy.BacktestingStrategy):
    """
    This is a dummy strategy to illustrate the use of pp data structures.
    """
    
    def __init__(self, feed, instrument, vwapWindowSize, threshold):
        super(PivotPointMomentum, self).__init__(feed)
        self._instrument = instrument
        self._vwap = vwap.VWAP(feed[instrument], vwapWindowSize)
        self._pp = pivotpoints.PivotPointsSequenceBased(feed[instrument], vwapWindowSize, 1,
                                                        pivotpoints.PivotPointsPeriod.daily)
        self._pp_e = pivotpoints.PivotPointsEventBased(feed[instrument], vwapWindowSize, 1,
                                                        pivotpoints.PivotPointsPeriod.daily)
        self._threshold = threshold
        self.getBroker().getFillStrategy().setVolumeLimit(None)

    def onEnterOk(self, position):
        execInfo = position.getEntryOrder().getExecutionInfo()
        self.info("BUY at $%.2f" % (execInfo.getPrice()))

    def onEnterCanceled(self, position):
        self.info("onEnterCanceled")
        self.__position = None

    def onExitOk(self, position):
        execInfo = position.getExitOrder().getExecutionInfo()
        self.info("SELL at $%.2f" % (execInfo.getPrice()))
        self.__position = None

    def onExitCanceled(self, position):
        # If the exit was canceled, re-submit it.
        self.info("onExitCanceled")
        self.__position.exitMarket()

    def getVWAP(self):
        return self._vwap

    def onBars(self, bars):
        vwap = self._vwap[-1]

        # -------------------------------------------------------------------
        # The only difference between the two is the way the data is presented and the different backend process.

        # Method 1: using PivotPointsSequenceBased
        pp = self._pp.getLastPivotLevel('PP') # unused but illustrates the point of getting the last value
        pp_list = self._pp.getPivotPointLevel('PP') # unused but illustrates the point of getting ALL level values

        # Method 2: using PivotPointsEventBased
        pp_e = self._pp_e.getCurrentLevels() # date is for the computed date

        if vwap is None:
            return

        assert pp[-1] == pp_e[-1]['PP']
        # -------------------------------------------------------------------

        # Dummy strategy
        shares = self.getBroker().getShares(self._instrument)
        price = bars[self._instrument].getClose()
        notional = shares * price

        # trades are only tracked once the net position becomes 0.
        if price > vwap * (1 + self._threshold) and notional <= 10000:
            self.enterLong(self._instrument, 1000, True)
        elif price < vwap * (1 - self._threshold) and notional >= -10000:
            self.enterShort(self._instrument, 1000, True)