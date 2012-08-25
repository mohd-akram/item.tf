"""TF2 API Script"""
import json
import csv
import re
import logging
from urllib2 import urlopen
from collections import defaultdict, OrderedDict

def isprice(string):
    """Check if string starts with a number"""
    return re.match(r'[0-9]',string)

def getschema(apikey):
    """Returns the schema"""
    url = 'http://api.steampowered.com/IEconItems_440/GetSchema/v0001/?key={}&language=en'.format(apikey)
    schema = json.loads(urlopen(url).read())

    return schema

def getitems(schema):
    """Returns an ordered dictionary of items in the schema where the key is defindex for
    each item"""
    items = OrderedDict()
    itemslist = schema['result']['items']

    for item in itemslist:
        items[item['defindex']] = item

    return items

def getattributes(schema):
    """Returns a dictionary with each attribute's name as key"""
    attributes = {}
    attributeslist = schema['result']['attributes']

    for attribute in attributeslist:
        attributes[attribute['name']] = attribute

    return attributes

def getitemsbyname(items):
    """Returns an ordered dictionary of items in the schema where the key is item_name for
    each item"""
    itemsbyname = OrderedDict()
    for item in items.values():
        name = item['item_name']
        if name not in itemsbyname:
            itemsbyname[name] = item
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

    pricesdict = defaultdict(dict)
    denominations = ['Key','Bud','Scrap']

    reader = csv.DictReader(pricesdata, fieldnames=['quality','class','name','price','lowprice','notes','color'])
    sheet = list(reader)[1:-1]

    for row in sheet:
        name = convertmarketname(row)
        price = row['price']
        quality = row['quality']
        lowprice = row['lowprice']

        if name in itemsbyname:
            if name.startswith('Gold Botkiller'):
                nongold = row.copy()
                nongold['name'] = name.replace('Gold ','')
                nongold['price'] = lowprice
                nongold['lowprice'] = lowprice = ''
                sheet.append(nongold)

            index = itemsbyname[name]['defindex']

            price = price.replace('ref','').replace('\n','').title()
            lowprice = lowprice.replace('ref','').replace('\n','').title()

            # Check if the price is a number and no denomination is specified
            if not any(d in price for d in denominations) and isprice(price):
                # Add Refined denomination
                price += ' Refined'

            if 'dirty' in row['name']:
                quality += ' (Dirty)'

            lowquality = 'Unique'

            if 'Dirty' in lowprice:
                lowquality += ' (Dirty)'

            lowprice = lowprice.replace('(Dirty)','')

            if price:
                pricesdict[index][quality] = price

            if lowprice and lowprice != '-':
                if not any(d in lowprice for d in denominations) and isprice(lowprice):
                    lowprice += ' Refined'

                pricesdict[index][lowquality] = lowprice

    return pricesdict

def getweapontags():
    return ['primary','secondary','melee','pda','pda2','building']

def getalltags():
    return (['hat','weapon','misc','tool','action','taunt','paint','token'] +
            getweapontags())

def getallclasses():
    return OrderedDict(
            [('Scout',['Scoot']),
            ('Soldier',['Solly']),
            ('Pyro',[]),
            ('Demoman',['Demo']),
            ('Heavy',[]),
            ('Engineer',['Engi','Engie']),
            ('Medic',[]),
            ('Sniper',[]),
            ('Spy',[])])

def getstoreprice(item, storeprices):
    """Get store price of item"""
    index = item['defindex']
    storeprice = ''

    if index in storeprices:
        storeitem = storeprices[index]
        storeprice = str(round(storeitem['prices']['USD']/100.00,2))

    return storeprice

def getmarketprice(item, marketprices):
    """Get market price of item"""
    index = item['defindex']
    marketprice = {}

    if index in marketprices:
        marketprice = marketprices[index]

    return marketprice

def getitemattributes(item, allattributes):
    """Get attributes of item"""
    attributelist = []
    if 'attributes' in item:
        attributes = item['attributes']
        for a in attributes:
            value = a['value']

            attribute = allattributes[a['name']]
            if not attribute['hidden'] and 'description_string' in attribute:
                description = attribute['description_string'].replace('%s1','{:g}')
                descformat = attribute['description_format']

                if descformat == "value_is_percentage":
                	value = (value * 100) - 100

                elif descformat == "value_is_inverted_percentage":
                	value = 100 - (value * 100)

                elif descformat == "value_is_additive_percentage":
                	value *= 100

                description = description.format(value)

                attrdict = {'description':description,'type':attribute['effect_type']}
                attributelist.append(attrdict)

    order = ['neutral','positive','negative']

    return sorted(attributelist,key=lambda k: order.index(k['type']))

def convertmarketname(row):
    """Changes the market name to match the proper TF2 name"""
    translations = {'Meet the Medic (clean)':'Taunt: The Meet the Medic',
                    'High-Five (clean)\n':'Taunt: The High Five!',
                    'Schadenfreude (clean)':'Taunt: The Schadenfreude',
                    'Key': 'Mann Co. Supply Crate Key',
                    'Mann Co. Supply Crate (series 40)':'Salvaged Mann Co. Supply Crate',
                    'Enemies Gibbed':'Strange Part: Gib Kills',
                    "HHH's Axe (clean)":"Horseless Headless Horsemann's Headtaker",
                    'Unusual Haunted Metal scrap (dirty)':'Haunted Metal Scrap',
                    'Ghastlier/Ghastlierest Gibus':'Ghastlierest Gibus',
                    'Hazmat Headcase':'HazMat Headcase',
                    'Spine-Chilling Skull 2010 (clean)':'Spine-Chilling Skull',
                    "Color of a Gentlemann's Business Pants":"The Color of a Gentlemann's Business Pants",
                    '\tColor No. 216-190-216 (Pink)':"Color No. 216-190-216",
                    "Zephaniah's Greed":"Zepheniah's Greed",
                    'Bolgan Helmet':'Bolgan',
                    'Full Head of Steam (dirty)':'Full Head Of Steam'}

    name = row['name']
    if name in translations:
        name = translations[name]
    elif row['quality'] == 'Strange Part':
        name = 'Strange Part: ' + name

    return name.replace(' (dirty)','').replace(' (clean)','').replace('\n','').replace('\t','')

def getitemclasses(item):
    """Get the TF2 classes that can use this item"""
    classes = []
    if 'used_by_classes' in item:
        classes = sorted(item['used_by_classes'],key=lambda k: getallclasses().keys().index(k))
    return classes

def getitemtags(item):
    """Get a list of tags that describe the item"""
    tags = []
    itemclass = item['item_class']

    if itemclass.endswith('_token'):
        tags.append('token')

    if 'item_slot' in item:
        slot = item['item_slot']

        if slot == 'head':
            tags.append('hat')
        else:
            if slot in getweapontags() and itemclass != 'slot_token':
                tags.append('weapon')

            tags.append(slot)

    if item['item_type_name'] == 'Special Taunt':
        tags.append('taunt')

    if 'tool' in item:
        tags.append('tool')

        if item['tool']['type'] == 'paint_can':
            tags.append('paint')

    return tags