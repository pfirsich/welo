import re
from datetime import datetime, date

def splitUnit(s):
    matches = re.findall(r"(\-?[0-9\.]+)\s*([A-z\"'\(\)]+)", s)
    if len(matches) == 0:
        raise ValueError
    return [(float(m[0]), m[1].strip().lower()) for m in matches]

def roundStr(v, digits=0):
    if v == int(v):
        return str(int(v))
    else:
        return str(round(v, digits))

# internal data is always SI base units

class Duration(object):
    def __init__(self, s):
        if isinstance(s, Duration):
            self.seconds = s.seconds
        elif isinstance(s, int) or isinstance(s, float):
            self.seconds = s
        else:
            s = s.strip()

            m = re.match(r"^([0-9]+):([0-9]+)$", s)
            if m:
                hours, minutes = int(m.group(1)), int(m.group(2))
                self.seconds = hours * 60 * 60 + minutes * 60
                return

            #m = re.match(r"^(?:([0-9\.])+h)?\s*(?:([0-9\.])+m(?:in)?)?$", s)
            self.seconds = 0
            try:
                for val, unit in splitUnit(s):
                    if unit == "m" or unit == "min":
                        self.seconds += val * 60
                    elif unit == "h":
                        self.seconds += val * 60 * 60
                    else:
                        raise ValueError
            except ValueError:
                raise ValueError("'{}' is not a duration!".format(s))

    def min(self):
        return self.seconds / 60

    def h(self):
        return self.seconds / 60 / 60

    def hmin(self):
        h = int(self.h())
        m = int(self.min()) - h*60
        return h, m

    def __str__(self):
        h, m = self.hmin()
        if h == 0:
            return "{} min".format(m)
        else:
            if m == 0:
                return "{} h".format(h)
            else:
                return "{}h {}min".format(h, m)

class Time(object):
    def __init__(self, s=None):
        if s == None:
            self.datetime = datetime.now()
        elif isinstance(s, Time):
            self.datetime = s.datetime
        else:
            formats = ["%d.%m.%Y %H:%M", "%d.%m.%Y", "%Y.%m.%d %H:%M", "%Y.%m.%d"]
            for fmt in formats:
                try:
                    self.datetime = datetime.strptime(s, fmt)
                    return
                except ValueError:
                    pass

            try:
                hmOnly = datetime.strptime(s, "%H:%M")
                now = datetime.now()
                self.datetime = datetime.combine(now.date(), hmOnly.time())
                return
            except ValueError:
                pass

            raise ValueError("'{}' is not a time!".format(s))

    # https://stackoverflow.com/questions/2217488/age-from-birthdate-in-python/9754466#9754466
    def getAge(self):
        born = self.datetime
        today = date.today()
        age = today.year - born.year
        if today.month < born.month or (today.month == born.month and today.day - born.day):
            age -= 1
        return age

    def inPeriod(self, start, end):
        return self.datetime > start and self.datetime < end

    def __str__(self):
        return self.datetime.strftime("%d.%m.%Y %H:%M")

class Sex(object):
    def __init__(self, s):
        self.sex = s.strip().lower()
        if self.sex not in ["male", "female", "m", "f"]:
            raise ValueError
        else:
            if self.sex == "m":
                self.sex = "male"
            elif self.sex == "f":
                self.sex = "female"

    def __eq__(self, other):
        return self.sex == other.sex

    def __str__(self):
        return self.sex

Sex.sexes = [Sex("f"), Sex("female"), Sex("m"), Sex("male")]

class Length(object):
    def __init__(self, s):
        if isinstance(s, Length):
            self.meters = s.meters
        elif isinstance(s, int) or isinstance(s, float):
            self.meters = s
        else:
            s = s.strip()
            self.meters = 0
            try:
                for val, unit in splitUnit(s):
                    if unit == "cm":
                        self.meters += val / 100.0
                    elif unit == "m":
                        self.meters += val
                    elif unit == "ft" or unit == "'":
                        self.meters += val * 0.3048
                    elif unit == "in" or unit == "\"":
                        self.meters += val * 0.0254
                    else:
                        raise ValueError
            except ValueError:
                raise ValueError("'{}' is not a length!".format(s))

    def m(self):
        return self.meters

    def cm(self):
        return self.meters * 100

    def __str__(self):
        if self.meters < 1:
            return "{}cm".format(int(self.cm()))
        else:
            return "{}m".format(roundStr(self.meters, 2))

class Mass(object):
    def __init__(self, s):
        if isinstance(s, Mass):
            self.kilograms = s.kilograms
        elif isinstance(s, int) or isinstance(s, float):
            self.kilograms = s
        else:
            s = s.strip()
            self.kilograms = 0
            try:
                for val, unit in splitUnit(s):
                    if unit == "g":
                        self.kilograms += val / 1000.0
                    elif unit == "kg":
                        self.kilograms += val
                    elif unit == "lb" or unit == "lbs":
                        self.kilograms += val * 0.453592
                    elif unit == "egg" or unit == "egg(m)":
                        self.kilograms += val * 0.058
                    elif unit == "egg(l)":
                        self.kilograms += val * 0.063
                    else:
                        raise ValueError("Unknown unit '{}'".format(unit))
            except ValueError as e:
                raise ValueError("'{}' is not a mass! - {}".format(s, e))

    def g(self):
        return self.kilograms * 1000

    def kg(self):
        return self.kilograms

    def __str__(self):
        kg = self.kg()
        if kg < 1:
            return "{}g".format(roundStr(self.g(), 1))
        else:
            return "{}kg".format(roundStr(kg, 1))

    def __mul__(self, factor):
        assert isinstance(factor, float) or isinstance(factor, int)
        return Mass(self.kilograms * factor)

    def __sub__(self, other):
        assert isinstance(other, Mass)
        return Mass(self.kilograms - other.kilograms)

    def __lt__(self, other):
        assert isinstance(other, Mass)
        return self.kilograms < other.kilograms

    def __neg__(self):
        return Mass(-self.kilograms)

    def __add__(self, other):
        assert isinstance(other, Mass)
        return Mass(self.kilograms + other.kilograms)

    def __iadd__(self, other):
        assert isinstance(other, Mass)
        self.kilograms += other.kilograms
        return self

    def __truediv__(self, other):
        if isinstance(other, Mass):
            return self.kilograms / other.kilograms
        elif isinstance(other, int) or isinstance(other, float):
            return Mass(self.kilograms / other)
        else:
            assert isinstance(other, Mass) or isinstance(other, int) or isinstance(other, float)

class Energy(object):
    def __init__(self, s):
        if isinstance(s, Energy):
            self.joules = s.joules
        elif isinstance(s, int) or isinstance(s, float):
            self.joules = s
        else:
            s = s.strip()
            self.joules = 0
            try:
                for val, unit in splitUnit(s):
                    if unit == "cal":
                        self.joules += val * 4.184
                    elif unit == "kcal":
                        self.joules += val * 4184
                    elif unit == "j":
                        self.joules += val
                    elif unit == "kj":
                        self.joules += val * 1000
                    else:
                        raise ValueError
            except ValueError:
                raise ValueError("'{}' is not an energy!".format(s))

    def kJ(self):
        return self.joules / 1000.0

    def kcal(self):
        return self.joules * 0.000239006

    def __str__(self):
        return "{}kcal".format(int(self.kcal()))

    def __mul__(self, factor):
        assert isinstance(factor, float) or isinstance(factor, int)
        return Energy(self.joules * factor)

    def __iadd__(self, other):
        assert isinstance(other, Energy)
        self.joules += other.joules
        return self

class Activity(object):
    def __init__(self, s):
        if isinstance(s, Activity):
            self.activity = s.activity
        elif isinstance(s, int) or isinstance(s, float):
            self.activity = s
        else:
            s = s.strip()
            m = re.match(r"([0-9\.]+).*", s)
            if m:
                self.activity = float(m.group(1))
            else:
                raise ValueError("'{}' is not an activity!".format(s))

    def __str__(self):
        s = str(roundStr(self.activity, 2))
        if self.activity < 1.4:
            s += " (extremely inactive)"
        elif self.activity < 1.7:
            s += " (sedentary)"
        elif self.activity < 2.0:
            s += " (moderately active)"
        elif self.activity < 2.4:
            s += " (vigorously active)"
        else:
            s += " (extremely active)"
        return s

def fromStr(s):
    assert isinstance(s, str)

    try:
        return Mass(s)
    except ValueError:
        pass

    try:
        return Length(s)
    except ValueError:
        pass

    try:
        return Energy(s)
    except ValueError:
        pass

    try:
        # This has to be after Length, because "m" is abused here for minutes
        # when actually it should be assumed that it refers to meters
        return Duration(s)
    except ValueError:
        pass

    try:
        # This is after Duration so 01:02 is a duration and not a time by default
        return Time(s)
    except ValueError:
        pass

    try:
        return Sex(s)
    except ValueError:
        pass

    try:
        return Activity(s)
    except ValueError:
        pass

    raise ValueError("'{}' does not match any quantity type!".format(s))

def assertEqual(a, b):
    if isinstance(a, float) or isinstance(b, float):
        eq = (a - b) / (a + b) < 0.01
    else:
        eq = a == b

    if not eq:
        print("{} != {}".format(a, b))
        raise AssertionError

if __name__ == "__main__":
    assertEqual(Duration("65 m").seconds, 65*60)
    assertEqual(fromStr("65min").seconds, 65*60)
    assertEqual(fromStr("65 min").seconds, 65*60)
    assertEqual(fromStr("1h5min").seconds, 65*60)
    assertEqual(fromStr("1h 5min").seconds, 65*60)
    assertEqual(fromStr("01:05").seconds, 65*60)
    assertEqual(fromStr("1:5").seconds, 65*60)
    assertEqual(str(Duration(60*60)), "1 h")
    assertEqual(str(Duration(59*60)), "59 min")
    assertEqual(str(Duration(61*60)), "1h 1min")

    assertEqual(fromStr("m").sex, "male")
    assertEqual(fromStr("male").sex, "male")
    assertEqual(fromStr("f").sex, "female")
    assertEqual(fromStr("female").sex, "female")
    assertEqual(str(Sex("m")), "male")
    assertEqual(str(Sex("male")), "male")
    assertEqual(str(Sex("f")), "female")
    assertEqual(str(Sex("female")), "female")

    assertEqual(fromStr("183cm").meters, 1.83)
    assertEqual(fromStr("183 cm").meters, 1.83)
    assertEqual(fromStr("1.83m").meters, 1.83)
    assertEqual(fromStr("1.8m").meters, 1.8)
    assertEqual(fromStr("1m83cm").meters, 1.83)
    assertEqual(fromStr("6ft").meters, 1.83)
    assertEqual(fromStr("6ft0in").meters, 1.83)
    assertEqual(fromStr("6'0\"").meters, 1.83)
    assertEqual(str(Length(1.8)), "1.8m")
    assertEqual(str(Length(1.83)), "1.83m")
    assertEqual(str(Length(0.9)), "90cm")
    assertEqual(str(Length(0.04)), "4cm")
    assertEqual(str(Length(0.94)), "94cm")

    assertEqual(fromStr("112 kg").kilograms, 112)
    assertEqual(fromStr("112kg").kilograms, 112)
    assertEqual(fromStr("112000 g").kilograms, 112)
    assertEqual(fromStr("246 lb").kilograms, 112)
    assertEqual(fromStr("246 lbs").kilograms, 112)
    assertEqual(fromStr("246lbs").kilograms, 112)
    assertEqual(str(Mass(112)), "112kg")
    assertEqual(str(Mass(112.5)), "112.5kg")
    assertEqual(str(Mass(112.55)), "112.5kg")
    assertEqual(str(Mass(0.5)), "500g")

    assertEqual(fromStr("1000 kcal").joules, 4184000)
    assertEqual(fromStr("1000000 cal").joules, 4184000)
    assertEqual(fromStr("4184000 J").joules, 4184000)
    assertEqual(fromStr("4184 kJ").joules, 4184000)
    assertEqual(str(Energy(2000)), "0kcal")
    assertEqual(str(Energy(4184000)), "1000kcal")

    assertEqual(fromStr("27.02.1992").datetime, datetime(1992, 2, 27))
    assertEqual(fromStr("27.02.1992 18:30").datetime, datetime(1992, 2, 27, hour=18, minute=30))
    assertEqual(fromStr("1992.02.27").datetime, datetime(1992, 2, 27))
    assertEqual(fromStr("1992.02.27 18:30").datetime, datetime(1992, 2, 27, hour=18, minute=30))
    print("Check if this is now yourself:", str(Time()))

    print("All tests passed!")
