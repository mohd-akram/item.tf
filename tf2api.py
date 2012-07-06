"""TF2 API Script"""
import json
import csv
import re
import logging
from urllib2 import urlopen
from collections import OrderedDict

def hasdigit(string):
    regex = re.compile(r'[0-9]')
    return regex.match(string)

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

def getmarketprices(items):
    """Get market prices from tf2spreadsheet.blogspot.com
    Returns a dictionary where the key is defindex and value is a dictionary of
    prices for the item"""
    url = 'https://spreadsheets.google.com/pub?key=0AnM9vQU7XgF9dFM2cldGZlhweWFEUURQU2pmOGJVMlE&output=csv'
    pricesdata = urlopen(url)

    itemsbyname = {}
    pricesdict = {}

    reader = csv.DictReader(pricesdata, fieldnames=['quality','class','name','price','lowprice','notes','color'])
    sheet = list(reader)[1:-1]

    for idx in items:
        itemsbyname[items[idx]['item_name']] = idx

    for row in sheet:
        name = convertmarketname(row['name'])
        price = row['price']
        quality = row['quality']
        lowprice = row['lowprice']

        denominations = ['Key','Bud','Scrap']
        pricedict = {}

        if name in itemsbyname:
            index = itemsbyname[name]

            price = price.replace('ref','').replace('\n','').title()
            lowprice = lowprice.replace('ref','').replace('\n','').title()

            # Check if the price is a number and no denomination is specified
            if not any(d in price for d in denominations) and hasdigit(price):
                # Add Refined denomination
                price = price + ' Refined'

            pricedict[quality] = price

            lowquality = 'Unique'

            if lowprice != '-':
                if not any(d in lowprice for d in denominations):
                    lowprice = lowprice + ' Refined'

                pricedict[lowquality] = lowprice

            pricesdict[index] = pricedict

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
        storeprice = storeitem['prices']['USD']/100.00

    return storeprice

def getmarketprice(item, marketprices):
    """Get market price of item"""
    index = item['defindex']
    marketprice = {}

    if index in marketprices:
        marketprice = marketprices[index]

    return marketprice

def convertmarketname(name):
    """Changes the market name to match the proper TF2 name"""
    translations = {'Meet the Medic (clean)':'Taunt: The Meet the Medic',
                    'High-Five (clean)\n':'Taunt: The High Five!'}

    if name in translations:
        name = translations[name]

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
    if item['item_class'].startswith('tf_weapon'):
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