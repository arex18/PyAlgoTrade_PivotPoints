# PyAlgoTrade Pivot Points Technical Indicator

[PyAlgoTrade](https://gbeced.github.io/pyalgotrade/) has inbuilt technicals and supports TA-Lib integration. 
Unfortunately, none of them include pivot points (PP).

This extension addresses that.

## Files

This is a working repo of the PP:
* main.py is just to execute the dummy strategy that instantiates the PP
* strategies/PivotPoints.py is the dummy strategy called from main. It is meant to
show how PP are called and the data structures. The PP themselves aren't used
in the strategy.
* data/forex/EURUSD1_small_2.csv. Self explanatory.
* technicals/pivotpoints. This is the file which should be put together with the other
PyAlgoTrade technicals, so an import would look like: 

```from pyalgotrade.technical import vwap, pivotpoints.```

There are 2 ways that the PP can be instantiated, and they differ in the way the data
is returned and the underlying library process. Nothing else. Both were left here for reference
but you should only use one method.

```   
# Method 1    
self._pp = pivotpoints.PivotPointsSequenceBased(feed[instrument], vwapWindowSize, 1, pivotpoints.PivotPointsPeriod.daily)
        
# Method 2
self._pp_e = pivotpoints.PivotPointsEventBased(feed[instrument], vwapWindowSize, 1, pivotpoints.PivotPointsPeriod.daily)
```

See the strategy example for more info.