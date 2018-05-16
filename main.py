import os
import argparse
import json
from collections import OrderedDict as odict
from datetime import datetime, date, timedelta, time
import re

import appdirs

import quantities as q
import fddb

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
    print("---")

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
            return bmr
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
                        print("You may also paste a link to a fddb.info site in the first prompt.")
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

    def eatInfo(self, startTime=None):
        if startTime:
            startTime = startTime.datetime
        else:
            startTime = datetime.combine(date.today(), time(0, 0))

        totalNutriInfo = NutriInfoAccumulator()
        meals = list(self.getMeals(startTime))

        if len(meals) > 0:
            for meal in meals:
                self.printMeal(meal)
                totalNutriInfo.add(food["nutriInfo"] for food in meal["food"])

            print("# In total since {}".format(startTime.strftime("%d.%m.%Y %H:%M")))
            totalNutriInfo = totalNutriInfo.getTotal()
            for key in totalNutriInfo:
                print("{}: {}".format(key, totalNutriInfo[key]))
        elif len(self.data["meals"]) > 0:
            print("You haven't eaten today yet.")
            timeDelta = datetime.now() - q.Time(self.data["meals"][-1]["time"]).datetime
            print("Your last meal was {} ago.".format(timedeltaStr(timeDelta)))

def bmiStr(bmi):
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
    parser = argparse.ArgumentParser(prog="welo", description="")
    subparsers = parser.add_subparsers(dest="command", help="")
    subparsers.required = True

    configParser = subparsers.add_parser("config")
    configParser.add_argument("datafile", nargs="?", type=str, help="")
    configParser.add_argument("--height", "-e", type=q.Length, help="")
    configParser.add_argument("--activity", "-a", type=q.Activity, help="")
    configParser.add_argument("--birthday", "-b", type=q.Time, help="")
    configParser.add_argument("--sex", "-s", type=q.Sex, help="")
    configParser.add_argument("--goalweight", "-g", type=q.Mass, help="")

    eatParser = subparsers.add_parser("eat")
    # food can be "<weight> leftovers"
    eatParser.add_argument("food", nargs="*", help="A repeating list of weight and food name pairs.")
    eatParser.add_argument("--name", "-n", type=str, help="The name of the meal.")
    eatParser.add_argument("--time", "-t", type=q.Time, help="The time of the meal.")
    eatParser.add_argument("--dry", "-d", action="store_true", help="If given, the meal will not be saved, but only the output will be shown and nutritional information about the food will be cached.")
    eatParser.add_argument("--undo", "-u", action="store_true", help="If given, undo last meal or the one at --time.")
    eatParser.add_argument("--resize", "-r", help="")
    eatParser.add_argument("--portion", "-p", help="")

    weightParser = subparsers.add_parser("weight")
    weightParser.add_argument("weight", nargs="?", type=q.Mass, help="The new weight.")
    weightParser.add_argument("--time", "-t", type=q.Time, help="The time of the weight measurement.")

    workoutParser = subparsers.add_parser("workout")
    workoutParser.add_argument("name", nargs="?", type=str, help="The name of the activity.")
    workoutParser.add_argument("duration", nargs="?", type=q.Duration, help="The duration of the activity.")
    workoutParser.add_argument("energy", nargs="?", type=q.Energy, help="The amount of energy used for the activity.")
    # TODO: Use energy / duration to estimate physical activity level

    tagParser = subparsers.add_parser("tag")
    tagParser.add_argument("tag", nargs="*", type=str, help="A list of tags. You may add tag parameters in brackets: 'mytag(param, param)'.")

    sleepParser = subparsers.add_parser("sleep")
    sleepParser.add_argument("time", help="This may either be a duration or a start time, if end time is given too.")
    sleepParser.add_argument("endtime", help="The end time.")

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
    else:
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

            print("{}, {}, {}".format(data.getConfig("sex"), data.getConfig("height"), data.getConfig("birthday").getAge()))
            print("activity: {}".format(data.getConfig("activity")))
            print("weight: {}, bmi: {}".format(data.getConfig("weight"), bmiStr(data.getBmi())))
            print("goal weight: {}".format(data.getConfig("goalWeight")))
            print()
            bmr = data.getBmr()
            print("Basal metabolic rate: {} kcal/day".format(bmr))
            activity = data.getActivity()
            if bmr and activity:
                print("Metabolic rate: {} kcal/day".format(bmr * activity))

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

        elif args.command == "tag":
            pass

        elif args.command == "sleep":
            pass

        elif args.command == "weight":
            if args.weight:
                data.addWeight(args.weight, args.time)
            else:
                data.printWeight()

        elif args.command == "workout":
            if args.name:
                if not args.duration:
                    quit("Please specify a duration")
            else:
                pass

if __name__ == "__main__":
    main()
