import re
from collections import OrderedDict as odict

import requests

import quantities as q

# exampmles from 16.05.2018
"""
<div class='itemsec2012'><h2 style='padding:0px;'>Nährwerte für  100 g</h2></div>
<div style='background-color:#f0f5f9;padding:2px 4px;'><div class='sidrow'><a href='https://fddb.info/db/de/lexikon/brennwert/index.html' style='font-weight:bold;'>Brennwert</a></div><div>996 kJ</div></div>
<div style='padding:2px 4px;'><div class='sidrow'><span style='font-weight:bold;'>Kalorien</span></div><div>238 kcal</div></div>
<div style='background-color:#f0f5f9;padding:2px 4px;'>
<div class='sidrow'><a href='https://fddb.info/db/de/lexikon/protein/index.html' style='font-weight:bold;'>Protein</a></div><div>17 g</div></div>
<div style='padding:2px 4px;'><div class='sidrow'><a href='https://fddb.info/db/de/lexikon/kohlenhydrate/index.html' style='font-weight:bold;'>Kohlenhydrate</a></div><div>2 g</div></div>
<div style='background-color:#f0f5f9;padding:2px 4px;'><div class='sidrow'><a href='https://fddb.info/db/de/lexikon/fett/index.html' style='font-weight:bold;'>Fett</a></div><div>18 g</div></div>
<div style='padding:2px 4px;'><div class='sidrow'><a href='https://fddb.info/db/de/lexikon/ballaststoffe/index.html' style=''>Ballaststoffe</a></div><div>0 g</div></div>
<div style='background-color:#f0f5f9;padding:2px 4px;'><div class='sidrow'><a href='https://fddb.info/db/de/lexikon/broteinheiten/index.html' style=''>Broteinheiten</a></div><div>0,2</div></div>
<div style='padding:2px 4px;'><div class='sidrow'><span style=''>Cholesterin</span></div><div>46 mg</div></div>
<div style='background-color:#f0f5f9;padding:2px 4px;'><div class='sidrow'><span style=''>Wassergehalt</span></div><div>95%</div></div>
"""

"""
<div class='itemsec2012'><h2 style='padding:0px;'>Data for  100 g</h2></div>
<div style='background-color:#f0f5f9;padding:2px 4px;'><div class='sidrow'><span style='font-weight:bold;'>Calorific value</span></div><div>1100 kJ</div></div>
<div style='padding:2px 4px;'><div class='sidrow'><span style='font-weight:bold;'>Calories</span></div><div>263 kcal</div></div>
<div style='background-color:#f0f5f9;padding:2px 4px;'><div class='sidrow'><span style='font-weight:bold;'>Protein</span></div><div>17.1 g</div></div>
<div style='padding:2px 4px;'><div class='sidrow'><span style='font-weight:bold;'>Carbohydrates</span></div><div>1.8 g</div></div>
<div style='background-color:#f0f5f9;padding:2px 4px;'><div class='sidrow'><a href='https://fddb.info/db/en/encyclopaedia/fat/index.html' style='font-weight:bold;'>Fat</a></div><div>21 g</div></div>
<div style='padding:2px 4px;'><div class='sidrow'><span style=''>Cholesterol</span></div><div>65 mg</div></div>
<div style='background-color:#f0f5f9;padding:2px 4px;'><div class='sidrow'><span style=''>Water content</span></div><div>58%</div></div>
"""

knownKeys = {
    "Kalorien": "energy",
    "Protein": "protein",
    "Kohlenhydrate": "carbs",
    "Fett": "fat",
    "Ballaststoffe": "fiber",
    "davon Zucker": "sugar",

    "Calories": "energy",
    "Carbohydrates": "carbs",
    "Fat": "fat",
    "Dietary fibre": "fiber",
    "thereof Sugar": "sugar",
}

keyOrder = ["energy", "fat", "satFat", "carbs", "sugar", "fiber", "protein", "sodium"]

def getNutriInfo(url):
    r = requests.get(url)
    fields = re.findall(r"<div class='sidrow'><a href='.*?' style='.*?'>(.*?)</a></div><div>(.*?)</div></div>", r.text)
    fields += re.findall(r"<div class='sidrow'><span style='.*?'>(.*?)</span></div><div>(.*?)</div></div>", r.text)
    fields = [(field[0], field[1].replace(",", ".")) for field in fields]
    nutriInfo = odict()
    for name, val in fields:
        if name in knownKeys:
            nutriInfo[knownKeys[name]] = str(q.fromStr(val))
    for key in keyOrder:
        if key in nutriInfo:
            nutriInfo.move_to_end(key)
    return nutriInfo

if __name__ == "__main__":
    print(getNutriInfo("https://fddb.info/db/de/lebensmittel/galbani_mozzarella/index.html"))
    print(getNutriInfo("https://fddb.info/db/en/food/new_producer_mozzarella/index.html"))
