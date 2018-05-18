import argparse
from collections import OrderedDict as odict
from datetime import datetime, date, timedelta, time
import json
import os
import re

import appdirs

from . import quantities as q
from . import fddb

def promptNutriInfoField(name, target, key, typeClass, factor, optional):
    while True:
        s = input(name + "> ").strip()
        if len(s) == 0:
            if optional:
                break
            else:
                print("This property is mandatory.")
        else:
            try:
                q = typeClass(s) * factor
                target[key] = str(q)
                break
            except ValueError:
                print("Could not parse as {}".format(typeClass.__name__))

def promptNutriInfo(name):
    print("Please enter the nutritional information for '{}' (per 100g)".format(name))
    reference = input("reference amount (leave empty for 100g)> ").strip()
    if len(reference) > 0:
        if reference.startswith("http"):
            nutriInfo = fddb.getNutriInfo(reference)
            print("--- Downloaded nutritional information for '{}':".format(name))
            for key in nutriInfo:
                print("{}: {}".format(key, nutriInfo[key]))
            print("---")
            return nutriInfo
        reference = q.Mass(reference)
    else:
        reference = q.Mass(0.1)
    factor = 100 / reference.g()

    data = odict()

    promptNutriInfoField("energy", data, "energy", q.Energy, factor, False)
    promptNutriInfoField("fat", data, "fat", q.Mass, factor, False)
    promptNutriInfoField("saturated fats (of that fat)", data, "satFat", q.Mass, factor, True)
    promptNutriInfoField("carbohydrates", data, "carbs", q.Mass, factor, False)
    promptNutriInfoField("sugar (of those carbs)", data, "sugar", q.Mass, factor, True)
    promptNutriInfoField("fiber (of those carbs)", data, "fiber", q.Mass, factor, True)
    promptNutriInfoField("protein", data, "protein", q.Mass, factor, False)
    promptNutriInfoField("sodium", data, "sodium", q.Mass, factor, True)
    if not "sodium" in data:
        promptNutriInfoField("salt", data, "sodium", q.Mass, factor * 0.4, True)

    print("--- You entered:")
    for key in data:
        print("{}: {}".format(key, data[key]))
    print("---\n")

    return data

class NutriInfoAccumulator(object):
    def __init__(self, it=None):
        self.info = odict()
        if it:
            self.add(it)

    def add(self, it):
        for item in it:
            self += item

    def __iadd__(self, nutriInfo):
        for field in nutriInfo:
            v = q.fromStr(nutriInfo[field])
            if field in self.info:
                self.info[field] += v
            else:
                self.info[field] = v
        return self

    def getTotal(self):
        return self.info

def bmi(weight, height):
    return weight / (height*height)

def timedeltaStr(delta):
    d, m = delta.days, int(delta.seconds/60)
    h = int(m / 60)
    m -= h * 60
    ret = ""
    if d > 0:
        ret += "{}d ".format(d)
    if h > 0:
        ret += "{}h ".format(h)
    ret += "{}m".format(m)
    return ret

class DataWrapper(object):
    def __init__(self, data, path):
        self.data = data
        self.path = path

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=4)

    def setConfig(self, name, value):
        self.data["config"][name] = str(value)

    def getConfig(self, name):
        if name in self.data["config"]:
            return q.fromStr(self.data["config"][name])
        else:
            return None

    def getBmi(self):
        w, h = self.getConfig("weight"), self.getConfig("height")
        if w and h:
            return bmi(w.kg(), h.m())
        else:
            return None

    # https://en.wikipedia.org/wiki/Physical_activity_level
    def getActivity(self):
        a = self.getConfig("activity")
        # TODO: add workout information
        if a:
            return a.activity
        else:
            return None

    # https://en.wikipedia.org/wiki/Basal_metabolic_rate
    def getBmr(self):
        w, h, s, b = self.getConfig("weight"), self.getConfig("height"), self.getConfig("sex"), self.getConfig("birthday")
        if w and h and s and b:
            # Mifflin St Jeor Equation
            bmr = 10 * w.kg() + 6.25 * h.cm() - 5 * b.getAge()
            if s == q.Sex("male"):
                bmr += 5
            else:
                bmr -= 161
            return round(bmr)
        else:
            return None

    def getTotalEnergyExpenditure(self):
        activity = self.getActivity()
        bmr = self.getBmr()
        if activity and bmr:
            return round(activity * bmr)
        else:
            return None

    def addWeight(self, weight, time=None):
        if len(self.data["weight"]) > 0:
            last = self.data["weight"][-1]
            delta = weight - q.fromStr(last["weight"])
            if delta.kg() > 0:
                print("You are up {} since your last measurement on {} @ {}".format(delta, last["time"], last["weight"]))
            else:
                print("You are down {} since your last measurement on {} @ {}. Nice job!".format(-delta, last["time"], last["weight"]))

        self.data["weight"].append(odict([
            ("time", str(time or q.Time())),
            ("weight", str(weight)),
        ]))

        self.setConfig("weight", weight)

        if len(self.data["weight"]) > 1:
            lowestWeight = weight
            for other in self.data["weight"]:
                v = q.fromStr(other["weight"])
                if v < weight:
                    lowestWeight = v
            if lowestWeight == weight:
                print("This is your new lowest weight!")

        height = self.getConfig("height")
        if height:
            print("Your BMI is:", round(self.getBmi(), 2))

        goalWeight = self.getConfig("goalWeight")
        if goalWeight:
            delta = weight - goalWeight
            if delta.kg() > 0:
                print("You are {} away from your goal of {}!".format(delta, goalWeight))
            else:
                print("You hit your goal weight of {}!".format(goalWeight))

        # TODO: "You are X away from a healthy weight?" (too negative for a daily message)

        self.save()

    def printWeight(self, num=100):
        for weight in self.data["weight"]:
            print("{}: {}".format(q.Time(weight["time"]), q.Mass(weight["weight"])))

    def getMeals(self, startTime):
        endTime = startTime + timedelta(hours=24)
        filtered = (meal for meal in self.data["meals"] if q.Time(meal["time"]).inPeriod(startTime, endTime))
        for meal in sorted(filtered, key=lambda meal: q.Time(meal["time"]).datetime):
            yield meal

    def totalMealWeight(self, meal):
        return sum((q.fromStr(item["amount"]) for item in meal["food"]), q.Mass(0))

    def printMeal(self, meal):
        name = meal.get("name", "meal")
        print("# {} @ {}".format(name, meal["time"]))
        print(" + ".join('{} "{}"'.format(item["amount"], item["name"]) for item in meal["food"]))
        print("Total weight:", self.totalMealWeight(meal))
        totalNutriInfo = NutriInfoAccumulator(item["nutriInfo"] for item in meal["food"]).getTotal()
        for field in totalNutriInfo:
            print("{}: {}".format(field, totalNutriInfo[field]))
        print()

    def getMealByTime(self, time):
        if time == None:
            return -1, self.data["meals"][-1]
        for i, meal in enumerate(self.data["meals"]):
            if meal["time"] == str(time):
                return i, meal
        return None, None

    @staticmethod
    def getPortionFactor(portion, totalWeight):
        try:
            factor = float(portion)
        except ValueError:
            factor = q.Mass(portion) / totalWeight

        if factor < 0:
            factor = 1.0 + factor

        return factor

    @staticmethod
    def multiplyFoodItems(foodItems, factor):
        ret = []
        for item in foodItems:
            _item = odict()
            _item["name"] = item["name"]
            _item["amount"] = str(q.fromStr(item["amount"]) * factor)
            _item["nutriInfo"] = odict()
            for field in item["nutriInfo"]:
                _item["nutriInfo"][field] = str(q.fromStr(item["nutriInfo"][field]) * factor)
            ret.append(_item)
        return ret

    def eat(self, name, food, time, dry, portion):
        portionFactor = 1.0
        if portion:
            totalWeight = sum((q.Mass(w) for w in food[::2]), q.Mass(0))
            portionFactor = self.getPortionFactor(portion, totalWeight)

        meal = odict()
        meal["time"] = str(time or q.Time())
        if name:
            meal["name"] = name
        meal["food"] = []

        promptIntro = False
        for i in range(0, len(food), 2):
            weight = food[i+0]
            name = food[i+1]

            leftoversMatch = re.match(r"^leftovers(?:\((.*?)\))?$", name)
            if leftoversMatch:
                leftoversTime = leftoversMatch.group(1)
                i, leftoverMeal = self.getMealByTime(leftoversTime)
                if i == None:
                    quit("No meal found for that time!")

                factor = portionFactor
                factor *= self.getPortionFactor(food[0], self.totalMealWeight(leftoverMeal))
                meal["food"].extend(self.multiplyFoodItems(leftoverMeal["food"], factor))
            else:
                if name in self.data["nutriInfoCache"]:
                    nutriInfo = self.data["nutriInfoCache"][name]
                else:
                    if not promptIntro:
                        print("Some foods have unknown nutritional information. Please enter it below.")
                        print("You may leave the fields empty if you don't know or care.")
                        print("You may also paste a link to a fddb.info site in the first prompt.\n")
                        promptIntro = True
                    nutriInfo = promptNutriInfo(name)
                    self.data["nutriInfoCache"][name] = nutriInfo

                weight = q.Mass(weight)
                factor = weight.g() / 100
                totalNutriInfo = odict()
                for field in nutriInfo:
                    totalNutriInfo[field] = str(q.fromStr(nutriInfo[field]) * factor * portionFactor)

                meal["food"].append(odict([
                    ("name", name),
                    ("amount", str(weight * portionFactor)),
                    ("nutriInfo", totalNutriInfo)
                ]))

        self.printMeal(meal)

        if not dry:
            self.data["meals"].append(meal)

        self.save()

    def eatUndo(self, time=None):
        i, meal = self.getMealByTime(time)
        self.data["meals"].pop(i)
        self.save()

    def resizeMeal(self, newWeight, dry, time):
        i, meal = self.getMealByTime(time)

        print("Before resizing:")
        self.printMeal(meal)

        factor = self.getPortionFactor(newWeight, self.totalMealWeight(meal))
        meal["food"] = self.multiplyFoodItems(meal["food"], factor)
        self.printMeal(meal)

        if not dry:
            self.save()

    def printMealTotals(self, meals, printDeficit=True):
        totalNutriInfo = NutriInfoAccumulator()
        for meal in meals:
            totalNutriInfo.add(food["nutriInfo"] for food in meal["food"])

        print("# Total")
        totalNutriInfo = totalNutriInfo.getTotal()
        for key in totalNutriInfo:
            print("{}: {}".format(key, totalNutriInfo[key]))

        totalEnergyExpenditure = self.getTotalEnergyExpenditure()
        kcalTotal = totalNutriInfo["energy"].kcal()
        if printDeficit and totalEnergyExpenditure:
            deficit = round(totalEnergyExpenditure - kcalTotal)
            print()
            if deficit > 0:
                print("With your total energy expenditure being {} kcal/day, you are currently at a calorie deficit of {} kcal".format(
                    totalEnergyExpenditure, deficit))
            else:
                print("With your total energy expenditure being {} kcal/day, you are currently at a calorie surplus of {} kcal".format(
                    totalEnergyExpenditure, -deficit))

    def eatInfo(self, startTime=None):
        if startTime:
            startTime = startTime.datetime
        else:
            startTime = datetime.combine(date.today(), time(0, 0))

        meals = list(self.getMeals(startTime))

        if len(meals) > 0:
            print("Your meals since {}:\n".format(startTime.strftime("%d.%m.%Y %H:%M")))
            for meal in meals:
                self.printMeal(meal)
            self.printMealTotals(meals)
        elif len(self.data["meals"]) > 0:
            print("You haven't eaten today yet.")
            timeDelta = datetime.now() - q.Time(self.data["meals"][-1]["time"]).datetime
            print("Your last meal was {} ago.".format(timedeltaStr(timeDelta)))

    def nutriInfo(self, foodItem):
        foodItem = foodItem.strip().lower()
        if foodItem in self.data["nutriInfoCache"]:
            print("Nutritional information for 100g of '{}':".format(foodItem))
            for field, val in self.data["nutriInfoCache"][foodItem].items():
                print("{}: {}".format(field, val))
        else:
            # Find best matches
            print("No exact matches found.")
            print("Closest matches:")
            match = {item: foodItemNameMatchScore(foodItem, item) for item in self.data["nutriInfoCache"].keys()}
            displayMatches = []
            minMatch = max(2, len(foodItem) // 2)
            for item in sorted(match.keys(), key=lambda x: match[x], reverse=True):
                if match[item] >= minMatch:
                    displayMatches.append(item)
                    if len(displayMatches) >= 5:
                        break
            for item in displayMatches:
                print(item)

# return longest substrings first
def substrings(s, minLength=1):
    l = len(s)
    for sublen in range(l, minLength - 1, -1):
        for start in range(0, l - sublen + 1):
            yield s[start:start + sublen]

def foodItemNameMatchScore(ref, name):
    ref = ref.strip().lower()
    name = name.strip().lower()
    score = 0
    for sub in substrings(ref):
        if sub in name:
            score = len(sub)
            break
    return score

def bmiStr(bmi):
    if bmi == None:
        return None

    s = str(round(bmi, 2))
    if bmi < 15:
        s += " (very severely underweight)"
    elif bmi < 16:
        s += " (severely underweight)"
    elif bmi < 18.5:
        s += " (underweight)"
    elif bmi < 25:
        s += " (normal)"
    elif bmi < 30:
        s += " (overweight)"
    elif bmi < 35:
        s += " (moderately obese)"
    elif bmi < 40:
        s += " (severely obese)"
    elif bmi < 45:
        s += " (very severely obese)"
    elif bmi < 50:
        s += " (morbidly obese)"
    elif bmi < 60:
        s += " (super obese)"
    else:
        s += " (hyper obese)"
    return s

def main():
    parser = argparse.ArgumentParser(prog="welo", description="Weight and calorie tracker")
    subparsers = parser.add_subparsers(dest="command", help="")
    subparsers.required = True

    configParser = subparsers.add_parser("config", description="Set the current data file or information about yourself, to enable extra output regarding BMI, BMR, caloric deficit, etc.")
    configParser.add_argument("datafile", nargs="?", type=str, help="This will set your current data file that welo will save its data to. If that file does not exist, it will be created.")
    configParser.add_argument("--height", "-e", type=q.Length, help="Your height.")
    configParser.add_argument("--activity", "-a", type=q.Activity, help="Your physical activity level (PAL).")
    configParser.add_argument("--birthday", "-b", type=q.Time, help="Your birthday to determine age.")
    configParser.add_argument("--sex", "-s", type=q.Sex, help="Your sex.")
    configParser.add_argument("--goalweight", "-g", type=q.Mass, help="Your goal weight.")

    eatParser = subparsers.add_parser("eat", description="Log or get info about the food you ate.", epilog="""
'portion':
May either be a weight, but also a unitless number, representing a factor which is applied to the total weight of whatever it is referencing.
Both the weight and the factor can be negative in which case the portion represents the total amount of whatever it is referencing *minus* that portion.
For a meal that has a total weight of 1000g '0.2' would represent a portion of 200g, '-0.2' would represent a portion of 800g, so would '-200g'.
""")
    eatParser.add_argument("food", nargs="*", help="A repeating list of weight and food name pairs. May also be 'leftovers' which represents the last logged meal or 'leftovers(time)' with time being the time of the meal which leftovers should reference. For leftovers the weight is a 'portion' (see epilog of this help text)")
    eatParser.add_argument("--name", "-n", type=str, help="The name of the meal.")
    eatParser.add_argument("--time", "-t", type=q.Time, help="The time of the meal.")
    eatParser.add_argument("--dry", "-d", action="store_true", help="If given, the meal will not be saved, but only the output will be shown and nutritional information about the food items will be cached.")
    eatParser.add_argument("--undo", "-u", action="store_true", help="If given, undo last meal or the one at --time. Positional arguments (i.e. food) will be ignored.")
    eatParser.add_argument("--resize", "-r", help="Resize the last eaten meal or the one at --time. The parameter is a 'portion' (see epilog of this help text).")
    eatParser.add_argument("--portion", "-p", help="Only eat a portion of the meal. The parameter is a 'portion' ")

    weightParser = subparsers.add_parser("weight", description="Log new weight or show last weight measurements.")
    weightParser.add_argument("weight", nargs="?", type=q.Mass, help="The new weight.")
    weightParser.add_argument("--time", "-t", type=q.Time, help="The time of the weight measurement. Defaults to now.")

    workoutParser = subparsers.add_parser("workout", description="Log workouts")
    workoutParser.add_argument("name", nargs="?", type=str, help="The name of the activity.")
    workoutParser.add_argument("duration", nargs="?", type=q.Duration, help="The duration of the activity.")
    workoutParser.add_argument("energy", nargs="?", type=q.Energy, help="The amount of energy used for the activity.")
    # TODO: Use energy / duration to estimate physical activity level

    nutriInfoParser = subparsers.add_parser("nutriinfo", description="Show nutritional info about a food item or find similar food items.")
    nutriInfoParser.add_argument("fooditem", help="The food item to search for or get information about.")

    tagParser = subparsers.add_parser("tag", description="Add tags to days to include in potential analyses about your weight development.")
    tagParser.add_argument("tag", nargs="*", type=str, help="A list of tags. You may add tag parameters in brackets: 'mytag(param, param)'.")

    args = parser.parse_args()

    configPath = os.path.join(appdirs.user_config_dir("welo", False), "config.json")
    if os.path.isfile(configPath):
        with open(configPath) as f:
            config = json.load(f, object_pairs_hook=odict)
    else:
        quit("Please call 'welo config <datafile>' on first start!")

    if args.command == "config" and args.datafile:
        print("Set current data file to '{}'".format(args.datafile))
        config["dataFile"] = os.path.abspath(args.datafile)
        os.makedirs(os.path.dirname(configPath), exist_ok=True)
        with open(configPath, "w") as f:
            json.dump(config, f, indent=4)

        if not os.path.isfile(config["dataFile"]):
            print("Creating new data file '{}'..".format(config["dataFile"]))
            data = DataWrapper(odict([
                ("config", odict()),
                ("weight", []),
                ("workout", []),
                ("meals", []),
                ("nutriInfoCache", odict()),
            ]), args.datafile)
            data.save()

    if not os.path.isfile(config["dataFile"]):
        quit("Data file could not be found.")

    with open(config["dataFile"]) as f:
        data = DataWrapper(json.load(f, object_pairs_hook=odict), config["dataFile"])

    if args.command == "config":
        if args.height:
            data.setConfig("height", args.height)
        if args.activity:
            data.setConfig("activity", args.activity)
        if args.birthday:
            data.setConfig("birthday", args.birthday)
        if args.sex:
            data.setConfig("sex", args.sex)
        if args.goalweight:
            data.setConfig("goalWeight", args.goalweight)

        if args.height or args.activity or args.birthday or args.sex or args.goalweight:
            data.save()

        print("Data file: '{}'".format(config["dataFile"]))
        print("sex: {}".format(data.getConfig("sex")))
        print("height: {}".format(data.getConfig("height")))
        birthday = data.getConfig("birthday")
        print("age: {} years old".format(birthday.getAge() if birthday else None))
        print("activity: {}".format(data.getConfig("activity")))
        print("weight: {}, bmi: {}".format(data.getConfig("weight"), bmiStr(data.getBmi())))
        print("goal weight: {}".format(data.getConfig("goalWeight")))
        print()
        print("Basal metabolic rate: {} kcal/day".format(data.getBmr()))
        print("Total energy expenditure: {} kcal/day".format(data.getTotalEnergyExpenditure()))

    elif args.command == "eat":
        if args.undo:
            data.eatUndo(args.time)
            return

        if args.resize:
            data.resizeMeal(args.resize, args.dry, args.time)
            return

        if len(args.food) == 0:
            data.eatInfo(args.time)
        else:
            data.eat(args.name, args.food, args.time, args.dry, args.portion)

    elif args.command == "weight":
        if args.weight:
            data.addWeight(args.weight, args.time)
        else:
            data.printWeight()

    elif args.command == "nutriinfo":
        data.nutriInfo(args.fooditem)

    elif args.command == "tag":
        quit("Not implemented yet!")
        pass

    elif args.command == "workout":
        quit("Not implemented yet!")
        if args.name:
            if not args.duration:
                quit("Please specify a duration")
        else:
            pass

if __name__ == "__main__":
    main()
