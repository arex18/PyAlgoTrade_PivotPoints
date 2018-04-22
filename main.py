from strategies import PivotPoints
from pyalgotrade import bar
from pyalgotrade.barfeed import csvfeed
import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_filepath(relative_file_path):
    ''' Helper function to get the absolute filepath from root programmatically. '''
    filepath = os.path.join(ROOT_DIR, *relative_file_path.replace('/', ' ').split())
    return filepath

def get_generic_feed(instrument, relative_filepath, frequency):
    # feed.setBarFilter(csvfeed.DateRangeFilter(firstDate,endDate))
    feed = csvfeed.GenericBarFeed(frequency)
    feed.addBarsFromCSV(instrument, get_filepath(relative_filepath))
    return feed

def main(plot):
    # Miscellaneous settings
    instrument = "EURUSD1"
    frequency = bar.Frequency.MINUTE
    relative_filepath = 'data/forex/EURUSD1_small_2.csv'
    feed = get_generic_feed(instrument, relative_filepath, frequency)
    # ---------------------------------------------------------
    # Strategy settings
    vwapWindowSize = 30
    threshold = 0.001
    # ---------------------------------------------------------
    # Strategy
    strategy = PivotPoints.PivotPointMomentum(feed, instrument, vwapWindowSize, threshold)
    # ---------------------------------------------------------
    # Run Strategy
    strategy.run()
    # ---------------------------------------------------------

if __name__ == "__main__":
    main(True)