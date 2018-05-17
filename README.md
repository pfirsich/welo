# welo
welo is a command line weight and calorie tracker application.

Sadly many good weight and calorie tracker applications are mobile apps and often enough not free. Since I mostly eat at home and have a tendency to immediately make my own as soon as a single tiny feature does not entirely match my expectations or needs, I made this.

## Installation
Just clone or download the repository navigate to the root (containing `setup.py`) and call `pip install .`. This program requires Python 3.

## Setup
The first time you start welo you should call
```
welo config <path>
```
with path being a path to a JSON file that will contain all the data that welo collects.

If you want to enable extra output regarding your [BMI](https://en.wikipedia.org/wiki/Body_mass_index), [BMR (Basal Metabolic Rate)](https://en.wikipedia.org/wiki/Basal_metabolic_rate) (using the Mifflin St Jeor equations) and your calorie deficits, you should pass the other optional parameters. See `welo config --help`.

## Units
Currently all quantities passed to the program **must** include units. Imperial and metric units are supported, but output is only in metric units! Considering I took great care in treating units properly, it should be simple to add a switch that changes output to imperial units, but since I have no need for that, I didn't do it yet.

Also a lot of data is written back into JSON and therefore converted to strings and rounded inbetween a lot (unneccesarily so actually), so some results might appear very off (e.g. amounts might not add up to an accurate total). Most errors of this kind should be in the low percents, which I personally find acceptable enough to ignore it.

### Documentation / Examples
I took great care writing good help texts (pass `-h` or `--help`), which hopefully makes further documentation unnecessary. If there is something you don't understand, please open an issue or contact me in some other way!

To get an idea of what welo can do, have a look at these examples (I made this stuff up, since I don't want to include *that* much personal information):

```console
$ welo config test.json --height 1.85m --sex m --birthday 01.01.1990 --activity 1.4 --goalweight 85kg
Set current data file to 'test.json'
Creating new data file 'C:\Users\Joel\dev\python\welo\test.json'..
Data file: 'C:\Users\Joel\dev\python\welo\test.json'
sex: male
height: 1.85m
age: 28 years old
activity: 1.4 (sedentary)
weight: None, bmi: None
goal weight: 85kg

Basal metabolic rate: None kcal/day
Total energy expenditure: None kcal/day
```
A few `None`s appear in the output, because we haven't logged a weight yet.

```console
$ welo weight 100kg
Your BMI is: 29.22
You are 15kg away from your goal of 85kg!
```
A day later:
```console
$ welo weight 99kg
You are down 1kg since your last measurement on 17.05.2018 8:30 @ 100kg. Nice job!
This is your new lowest weight!
Your BMI is: 28.93
You are 14kg away from your goal of 85kg!
```
Don't pass a weight to output the last measurements:
```console
$ welo weight
16.05.2018 8:30: 100kg
17.05.2018 8:30: 99kg
```

The `welo config` output is now aware of your weight:
```console
$ welo config
Data file: 'C:\Users\Joel\dev\python\welo\test.json'
sex: male
height: 1.85m
age: 28 years old
activity: 1.4 (sedentary)
weight: 99kg, bmi: 28.93 (overweight)
goal weight: 85kg

Basal metabolic rate: 2011 kcal/day
Total energy expenditure: 2815 kcal/day
```

The cooler parts of welo are definitely it's calorie tracking features:
```console
$ welo eat 500g tomato 30g "olive oil"
Some foods have unknown nutritional information. Please enter it below.
You may leave the fields empty if you don't know or care.
You may also paste a link to a fddb.info site in the first prompt.

Please enter the nutritional information for 'tomato' (per 100g)
reference amount (leave empty for 100g)>
energy> 18kcal
fat> 0.2g
saturated fats (of that fat)>
carbohydrates> 2.6g
sugar (of those carbs)> 2.5g
fiber (of those carbs)> 1.3g
protein> 1g
sodium>
salt>
--- You entered:
energy: 18kcal
fat: 0.2g
carbs: 2.6g
sugar: 2.5g
fiber: 1.3g
protein: 1g
---

Please enter the nutritional information for 'olive oil' (per 100g)
reference amount (leave empty for 100g)> https://fddb.info/db/de/lebensmittel/naturprodukt_olivenoel/index.html
--- Downloaded nutritional information for 'olive oil':
energy: 857kcal
fat: 91.5g
carbs: 0g
sugar: 0g
fiber: 0g
protein: 0g
---

# meal @ 17.05.2018 13:00
500g "tomato" + 30g "olive oil"
Total weight: 530g
energy: 347kcal
fat: 28.4g
carbs: 13g
sugar: 12.5g
fiber: 6.5g
protein: 5g
```

As visible in the prompt input for "olive oil", you don't have to enter the nutritional information yourself, but can also paste a link to a [fddb.info](fddb.info) site. If you live in a different place or prefer other sites, open an issue and I might add it too! Also the nutritional information is then associated with that food item name ("tomato" and "olive oil" in this example), so you only have do to this once.

You may also change pass the time you had the meal, add a name (like "lunch", "dinner", etc.), "undo" meals or do a "dry run", which will not save the data, but show the output and cache the nutritional information for the food items. Use `welo eat --help` to get more information on this.

You can also only eat a portion of a meal (e.g. you made 1kg of pasta but only ate 500g):

```console
$ welo eat 1kg pasta --portion 0.5
# meal @ 17.05.2018 20:00
500g "pasta"
Total weight: 500g
energy: 735kcal
fat: 4.5g
carbs: 145g
sugar: 1g
fiber: 10g
protein: 20g
```

The `--portion` parameter can either be a unitless quantity, in which case it describes a factor to be applied to the full meal (0.5 meaning half of it). But you can also pass a weight, i.e. `--portion 500g` would have been equivalent in the example above.

It is also possible to pass negative numbers, which are then subtracted from the full meal. E.g. `--portion " -200g"` would mean that you ate 800g of the full 1kg (1000g). This works for the unitless factors as well (equivalent would be `--portion -0.2`). The quotes around and the space at the beginning of `-200g` are necessary because Pythons argparse module will confuse `-200g` with a switch otherwise.

You can see how much you ate today, by not passing food:
```console
$ welo eat
Your meals since 17.05.2018 00:00:

# meal @ 17.05.2018 13:00
500g "tomato" + 30g "olive oil"
Total weight: 530g
energy: 347kcal
fat: 28.4g
carbs: 13g
sugar: 12.5g
fiber: 6.5g
protein: 5g

# meal @ 17.05.2018 20:00
500g "pasta"
Total weight: 500g
energy: 735kcal
fat: 4.5g
carbs: 145g
sugar: 1g
fiber: 10g
protein: 20g

# Total
energy: 1082kcal
fat: 32.9g
carbs: 158g
sugar: 13.5g
fiber: 16.5g
protein: 25g

With your total energy expenditure being 2815 kcal/day, you are currently at a calorie deficit of 1733 kcal
```

The next day you can eat the leftovers, since you only eat half of it (`--portion 0.5`):
```console
$ welo eat 1.0 "leftovers(17.05.2018 20:00)"
# meal @ 18.05.2018 13:00
500g "pasta"
Total weight: 500g
energy: 735kcal
fat: 4.5g
carbs: 145g
sugar: 1g
fiber: 10g
protein: 20g
```

The time in brackets of `leftovers` points to the meal you are eating leftovers of. The time (and the brackets) can be ommited, in which case the last logged meal is used. Just like `--portion`, leftovers can take a unitless number or grams (both can be negative as well.)

### Unimplemented Commands
There are some unimplemented features that I might add in the future if I have the need, that are, so far, only added as stubs that produce error messages, but feel free to do it yourself and make a pull request! These include:

* `welo tags`: This would be used to do something like Ariel Faigon did with his experiments investigating the factors leading to his personal weight gain or weight loss using machine learning: [weight-loss](https://github.com/arielf/weight-loss).
* `welo workout`: Which would simply track the type, duration and intensity of workouts to help estimate the physical activity level and in turn the total energy expenditure more accurately.
