"""TF2 API Script"""
import json
import csv
import re
import logging
from urllib2 import urlopen
from collections import OrderedDict

def hasdigit(string):
    regex = re.compile(r'[0-9]')
    return regex.search(string)

def getitems(apikey):
    """Returns an ordered dictionary of items in the schema where the key is defindex for
    each item"""
    url = 'http://api.steampowered.com/IEconItems_440/GetSchema/v0001/?key={}&language=en'.format(apikey)
    schema = urlopen(url).read()

    items = OrderedDict()
    itemslist = json.loads(schema)['result']['items']

    for item in itemslist:
        items[item['defindex']] = item

    return items

def getduplicates():
    """Gets items that have the same name as another item
    This includes any stock weapons that are included twice"""
    stock = [10,11,12,23] + [i for i in range(190,213)]
    keys = [5049,5067,5072,5073]
    crates = [5041,5045]
    return keys + crates + stock

def getitemsbyname(items):
    duplicates = getduplicates()
    itemsbyname = {}
    for idx in items:
        if idx not in duplicates:
            itemsbyname[items[idx]['item_name']] = items[idx]
    return itemsbyname

def getstoreprices(apikey):
    """Returns a dictionary of store prices where the key is defindex for
    each item"""
    url = 'http://api.steampowered.com/ISteamEconomy/GetAssetPrices/v0001/?key={}&language=en&appid=440&currency=usd'.format(apikey)
    pricesdata = urlopen(url).read()

    prices = {}
    priceslist = json.loads(pricesdata)['result']['assets']

    for price in priceslist:
        prices[int(price['name'])] = price

    return prices

def getmarketprices(itemsbyname):
    """Get market prices from tf2spreadsheet.blogspot.com
    Returns a dictionary where the key is defindex and value is a dictionary of
    prices for the item"""
    url = 'https://spreadsheets.google.com/pub?key=0AnM9vQU7XgF9dFM2cldGZlhweWFEUURQU2pmOGJVMlE&output=csv'
    pricesdata = urlopen(url)

    pricesdict = {}
    denominations = ['Key','Bud','Scrap']

    reader = csv.DictReader(pricesdata, fieldnames=['quality','class','name','price','lowprice','notes','color'])
    sheet = list(reader)[1:-1]

    for row in sheet:
        name = convertmarketname(row)
        price = row['price']
        quality = row['quality']
        lowprice = row['lowprice']

        if name in itemsbyname:
            index = itemsbyname[name]['defindex']

            if not index in pricesdict:
                pricesdict[index] = {}

            price = price.replace('ref','').replace('\n','').title()
            lowprice = lowprice.replace('ref','').replace('\n','').title()

            # Check if the price is a number and no denomination is specified
            if not any(d in price for d in denominations) and hasdigit(price):
                # Add Refined denomination
                price += ' Refined'

            if price:
                pricesdict[index][quality] = price

            lowquality = 'Unique'

            if 'Dirty' in lowprice:
                lowquality += ' (Dirty)'

            lowprice = lowprice.replace('(Dirty)','')

            if lowprice and lowprice != '-':
                if not any(d in lowprice for d in denominations) and hasdigit(lowprice):
                    lowprice += ' Refined'

                pricesdict[index][lowquality] = lowprice

    return pricesdict

def getallitemtypes():
    return ['hat','weapon','misc','tool','action','taunt','paint']

def gettf2classes():
    scout = {'name':'Scout', 'aliases':['Scoot']}
    soldier = {'name':'Soldier', 'aliases':['Solly']}
    pyro = {'name':'Pyro', 'aliases':[]}
    demoman = {'name':'Demoman', 'aliases':['Demo']}
    heavy = {'name':'Heavy', 'aliases':[]}
    engineer = {'name':'Engineer', 'aliases':['Engi','Engie']}
    medic = {'name':'Medic', 'aliases':[]}
    sniper = {'name':'Sniper', 'aliases':[]}
    spy = {'name':'Spy', 'aliases':[]}

    classes = [scout,soldier,pyro,demoman,heavy,engineer,medic,sniper,spy]

    return classes

def getstoreprice(item, storeprices):
    """Get store price of item"""
    defindex = item['defindex']
    storeprice = ''

    if defindex in storeprices:
        storeitem = storeprices[defindex]
        storeprice = round(storeitem['prices']['USD']/100.00,2)

    return storeprice

def getmarketprice(item, marketprices):
    """Get market price of item"""
    index = item['defindex']
    marketprice = {}

    if index in marketprices:
        marketprice = marketprices[index]

    return marketprice

def convertmarketname(row):
    """Changes the market name to match the proper TF2 name"""
    translations = {'Meet the Medic (clean)':'Taunt: The Meet the Medic',
                    'High-Five (clean)\n':'Taunt: The High Five!',
                    'Key': 'Mann Co. Supply Crate Key',
                    'Mann Co. Supply Crate (series 40)':'Salvaged Mann Co. Supply Crate',
                    'Mann Co. Supply Crate (series 46)':'Scorched Crate',
                    'Enemies Gibbed':'Strange Part: Gib Kills',
                    "HHH's Axe (clean)":"Horseless Headless Horsemann's Headtaker",
                    'Unusual Haunted Metal scrap (dirty)':'Haunted Metal Scrap',
                    'Ghastlier/Ghastlierest Gibus':'Ghastlierest Gibus',
                    'Hazmat Headcase':'HazMat Headcase'}

    name = row['name']
    if name in translations:
        name = translations[name]
    elif row['quality'] == 'Strange Part':
        name = 'Strange Part: ' + name

    return name.replace(' (dirty)','').replace(' (clean)','')

def getitemclasses(item):
    """Get the TF2 classes that can use this item"""
    classes = []
    if 'used_by_classes' in item:
        classes = item['used_by_classes']
    return classes

def getitemtags(item):
    tags = []

    if isweapon(item):
        tags.append('weapon')
    if ishat(item):
        tags.append('hat')
    if ismisc(item):
        tags.append('misc')
    if isaction(item):
        tags.append('action')
    if istaunt(item):
        tags.append('taunt')
    if istool(item):
        tags.append('tool')
    if ispaint(item):
        tags.append('paint')

    return tags

def isweapon(item):
    if 'item_slot' in item:
        if (item['item_slot'] in ['primary','secondary','melee','pda','pda2']
            and item['item_class'] != 'slot_token'):
            return True

def ishat(item):
    if 'item_slot' in item:
        if item['item_slot'] == 'head':
            return True

def ismisc(item):
    if 'item_slot' in item:
        if item['item_slot'] == 'misc':
            return True

def isaction(item):
    if 'item_slot' in item:
        if item['item_slot'] == 'action':
            return True

def istaunt(item):
    if item['item_type_name'] == 'Special Taunt':
        return True

def istool(item):
    if 'tool' in item:
        return True

def ispaint(item):
    if istool(item):
        if item['tool']['type'] == 'paint_can':
            return True