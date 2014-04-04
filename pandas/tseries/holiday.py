from pandas import DateOffset, date_range, Series
from datetime import datetime, timedelta
from dateutil.relativedelta import MO, TU, WE, TH, FR, SA, SU

def next_monday(dt):
    '''
    If holiday falls on Saturday, use following Monday instead;
    if holiday falls on Sunday, use Monday instead
    '''
    if dt.weekday() == 5: 
        return dt + timedelta(2)
    elif dt.weekday() == 6: 
        return dt + timedelta(1)
    return dt

def next_monday_or_tuesday(dt):
    '''
    For second holiday of two adjacent ones!
    If holiday falls on Saturday, use following Monday instead;
    if holiday falls on Sunday or Monday, use following Tuesday instead
    (because Monday is already taken by adjacent holiday on the day before)
    '''
    dow = dt.weekday()
    if dow == 5 or dow == 6: 
        return dt + timedelta(2)
    elif dow == 0: 
        return dt + timedelta(1)
    return dt

def previous_friday(dt):
    '''
    If holiday falls on Saturday or Sunday, use previous Friday instead.
    '''
    if dt.weekday() == 5: 
        return dt - timedelta(1)
    elif dt.weekday() == 6: 
        return dt - timedelta(2)
    return dt

def sunday_to_monday(dt):
    '''
    If holiday falls on Sunday, use day thereafter (Monday) instead.
    '''
    if dt.weekday() == 6: 
        return dt + timedelta(1)
    return dt

def nearest_workday(dt):
    '''
    If holiday falls on Saturday, use day before (Friday) instead;
    if holiday falls on Sunday, use day thereafter (Monday) instead.
    '''
    if dt.weekday() == 5: 
        return dt - timedelta(1)
    elif dt.weekday() == 6:
        return dt + timedelta(1)
    return dt

class Holiday(object):
    '''
    Class that defines a holiday with start/end dates and rules
    for observance.
    '''
    def __init__(self, name, year=None, month=None, day=None, offset=None,
                 observance=None, start_date=None, end_date=None):
        self.name   =   name
        self.year   =   year
        self.month  =   month
        self.day    =   day
        self.offset =   offset
        self.start_date = start_date
        self.end_date   = end_date
        self.observance = observance
    
    def __repr__(self):
        info = ''
        if self.year is not None:
            info += 'year=%s, ' % self.year
        info += 'month=%s, day=%s, ' % (self.month, self.day)
        
        if self.offset is not None:
            info += 'offset=%s' % self.offset
            
        if self.observance is not None:
            info += 'observance=%s' % self.observance
        
        return 'Holiday: %s (%s)' % (self.name, info)
    
    def dates(self, start_date, end_date, return_name=False):
        '''
        Calculate holidays between start date and end date
        
        Parameters
        ----------
        start_date : starting date, datetime-like, optional
        end_date : ending date, datetime-like, optional
        return_name : bool, optional, default=False
            If True, return a series that has dates and holiday names.
            False will only return dates.
        '''
        if self.year is not None:
            return datetime(self.year, self.month, self.day)
        
        if self.start_date is not None:
            start_date = self.start_date
            
        if self.end_date is not None:
            end_date = self.end_date
        
        year_offset = DateOffset(years=1)   
        base_date = datetime(start_date.year, self.month, self.day)
        dates = date_range(base_date, end_date, freq=year_offset)
        holiday_dates = list(self._apply_rule(dates))
        if return_name:
            return Series(self.name, index=holiday_dates)
        
        return holiday_dates

    def _apply_rule(self, dates):   
        '''
        Apply the given offset/observance to an 
        iterable of dates.
        
        Parameters
        ----------
        dates : array-like
            Dates to apply the given offset/observance rule
        
        Returns
        -------
        Dates with rules applied
        '''
        if self.observance is not None:
            return map(lambda d: self.observance(d), dates)

        if not isinstance(self.offset, list):
            offsets =   [self.offset]
        else:
            offsets =   self.offset
            
        for offset in offsets:
            dates = map(lambda d: d + offset, dates)
            
        return dates

#----------------------------------------------------------------------
# Calendar class registration

holiday_calendars = {}
def register(cls):
    try:
        name = cls.name
    except:
        name = cls.__name__
    holiday_calendars[name] = cls
    
def get_calendar(name):
    '''
    Return an instance of a calendar based on its name.
    
    Parameters
    ----------
    name : str
        Calendar name to return an instance of
    '''
    return holiday_calendars[name]()

#----------------------------------------------------------------------
# Holiday classes
class HolidayCalendarMetaClass(type):
    def __new__(cls, clsname, bases, attrs):
        calendar_class = super(HolidayCalendarMetaClass, cls).__new__(cls, clsname, bases, attrs)
        register(calendar_class)
        return calendar_class

class AbstractHolidayCalendar(object):
    '''
    Abstract interface to create holidays following certain rules.
    '''
    __metaclass__ = HolidayCalendarMetaClass
    rules = []
    _holiday_start_date = datetime(1970, 1, 1)
    _holiday_end_date   = datetime(2030, 12, 31)
    _holiday_cache = None
    
    def __init__(self, name=None, rules=None):
        '''
        Initializes holiday object with a given set a rules.  Normally
        classes just have the rules defined within them.
        
        Parameters
        ----------
        name : str 
            Name of the holiday calendar, defaults to class name
        rules : array of Holiday objects
            A set of rules used to create the holidays.
        '''
        super(AbstractHolidayCalendar, self).__init__()
        if name is None:
            name = self.__class__.__name__
        self.name = name
        
        if rules is not None:
            self.rules = rules

    def holidays(self, start=_holiday_start_date, end=_holiday_end_date, return_name=False):
        '''
        Returns a curve with holidays between start_date and end_date
        
        Parameters
        ----------
        start : starting date, datetime-like, optional
        end : ending date, datetime-like, optional
        return_names : bool, optional
            If True, return a series that has dates and holiday names.
            False will only return a DatetimeIndex of dates.

        Returns
        -------
            DatetimeIndex of holidays
        '''
        if self.rules is None:
            raise Exception('Holiday Calendar %s does not have any '\
                            'rules specified' % self.name)

        holidays = None
        # If we don't have a cache or the dates are outside the prior cache, we get them again
        if self._cache is None or start < self._cache[0] or end > self._cache[1]: 
            for rule in self.rules:
                rule_holidays = rule.dates(start, end, return_name=True)
                if holidays is None:
                    holidays = rule_holidays
                else:
                    holidays = holidays.append(rule_holidays)
                    
            self._cache = (start, end, holidays.sort_index())
        
        holidays = self._cache[2]
        holidays = holidays[start:end]
        
        if return_name:
            return holidays
        else:
            return holidays.index
    
    @property
    def _cache(self):
        return self.__class__._holiday_cache
    
    @_cache.setter
    def _cache(self, values):
        self.__class__._holiday_cache = values

    @staticmethod
    def merge_class(base, other):
        '''
        Merge holiday calendars together.  The base calendar
        will take precedence to other. The merge will be done
        based on each holiday's name.
        
        Parameters
        ----------
        base : AbstractHolidayCalendar instance of array of Holiday objects
        other : AbstractHolidayCalendar instance or array of Holiday objects
        '''
        if isinstance(other, AbstractHolidayCalendar):
            other = other.rules
        if not isinstance(other, list):
            other = [other]
        other_holidays = dict((holiday.name, holiday) for holiday in other)
            
        if isinstance(base, AbstractHolidayCalendar):
            base = base.rules
        if not isinstance(base, list):
            base = [base]
        base_holidays = dict((holiday.name, holiday) for holiday in base)
        
        other_holidays.update(base_holidays)
        return other_holidays.values()

    def merge(self, other, inplace=False):
        '''
        Merge holiday calendars together.  The caller's class
        rules take precedence.  The merge will be done
        based on each holiday's name.
        
        Parameters
        ----------
        other : holiday calendar
        inplace : bool (default=False)
            If True set rule_table to holidays, else return array of Holidays
        '''
        holidays    =   self.merge_class(self, other)
        if inplace:
            self.rules = holidays
        else:
            return holidays

    @staticmethod
    def merge_class(base, other):
        '''
        Merge holiday calendars together.  The base calendar
        will take precedence to other. The merge will be done
        based on each holiday's name.
        
        Parameters
        ----------
        base : AbstractHolidayCalendar instance of array of Holiday objects
        other : AbstractHolidayCalendar instance or array of Holiday objects
        '''
        if isinstance(other, AbstractHolidayCalendar):
            other = other.rules
        if not isinstance(other, list):
            other = [other]
        other_holidays = {holiday.name: holiday for holiday in other}
            
        if isinstance(base, AbstractHolidayCalendar):
            base = base.rules
        if not isinstance(base, list):
            base = [base]
        base_holidays = {holiday.name: holiday for holiday in base}
        
        other_holidays.update(base_holidays)
        return other_holidays.values()

    def merge(self, other, inplace=False):
        '''
        Merge holiday calendars together.  The caller's class
        rules take precedence.  The merge will be done
        based on each holiday's name.
        
        Parameters
        ----------
        other : holiday calendar
        inplace : bool (default=False)
            If True set rule_table to holidays, else return array of Holidays
        '''
        holidays    =   self.merge_class(self, other)
        if inplace:
            self.rules = holidays
        else:
            return holidays

USMemorialDay     = Holiday('MemorialDay', month=5, day=24, 
                            offset=DateOffset(weekday=MO(1)))
USLaborDay        = Holiday('Labor Day', month=9, day=1, 
                            offset=DateOffset(weekday=MO(1)))
USColumbusDay     = Holiday('Columbus Day', month=10, day=1,
                            offset=DateOffset(weekday=MO(2)))
USThanksgivingDay = Holiday('Thanksgiving', month=11, day=1, 
                            offset=DateOffset(weekday=TH(4)))
USMartinLutherKingJr = Holiday('Dr. Martin Luther King Jr.', month=1, day=1, 
                               offset=DateOffset(weekday=MO(3)))
USPresidentsDay      = Holiday('President''s Day', month=2, day=1, 
                               offset=DateOffset(weekday=MO(3)))

class USFederalHolidayCalendar(AbstractHolidayCalendar):
    '''
    US Federal Government Holiday Calendar based on rules specified
    by: https://www.opm.gov/policy-data-oversight/snow-dismissal-procedures/federal-holidays/
    '''
    rules = [ 
        Holiday('New Years Day', month=1,  day=1,  observance=nearest_workday), 
        USMartinLutherKingJr,
        USPresidentsDay,
        USMemorialDay,
        Holiday('July 4th', month=7,  day=4,  observance=nearest_workday),
        USLaborDay,
        USColumbusDay,
        Holiday('Veterans Day', month=11, day=11, observance=nearest_workday),
        USThanksgivingDay,
        Holiday('Christmas', month=12, day=25, observance=nearest_workday)
        ]
    
def HolidayCalendarFactory(name, base, other, base_class=AbstractHolidayCalendar):
    rules = AbstractHolidayCalendar.merge_class(base, other)
    calendar_class = type(name, (base_class,), {"rules": rules, "name": name})
    return calendar_class
