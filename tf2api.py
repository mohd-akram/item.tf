# coding=utf-8

"""This module is based on the Steam WebAPI and can be used to get information
about items in TF2. Using this module, you can obtain the item schema,
store prices, bundles, item sets and attributes for TF2.
You can also obtain market prices from the community spreadsheet.

There are also functions for parsing the information of each item.

"""
import json
import csv
from urllib2 import urlopen
from collections import defaultdict, OrderedDict

def isprice(string):
    """Check if string starts with a number"""
    if string:
        return string[0].isdigit()
    return False

def getschema(apikey):
    """Return the schema"""
    url = ('http://api.steampowered.com/IEconItems_440/GetSchema/v0001/'
           '?key={}&language=en'.format(apikey))

    return json.loads(urlopen(url).read())

def getitemsinfo(apikey, storeprices, indexes):
    """Return a dictionary of AssetClassInfo values with defindex as key"""
    url = ('http://api.steampowered.com/ISteamEconomy/GetAssetClassInfo/v0001/'
           '?key={0}&language=en&appid=440&class_count={1}'.format(apikey,
                                                                   len(indexes))
                                                                   )

    idtoindex = {}
    for n, index in enumerate(indexes):
        classid = storeprices[index]['classid']
        idtoindex[classid] = index
        url += '&classid{0}={1}'.format(n, classid)

    infobyid = json.loads(urlopen(url).read())['result']
    del infobyid['success']

    return {idtoindex[classid]:iteminfo for classid, iteminfo in
            infobyid.items()}

def getbundles(apikey, storeprices):
    """Return a dictionary of store bundles with defindex as key"""
    indexes = [index for index, price in storeprices.items()
               if 'Bundles' in price['tags']]
    return getitemsinfo(apikey, storeprices, indexes)

def getitemsets(schema):
    """Return a dictionary of itemsets with 'name' as key"""
    return {itemset['name']:itemset for itemset in
            schema['result']['item_sets']}

def getitems(schema):
    """Return an ordered dictionary of items in the schema where the key is
    defindex for each item"""
    return OrderedDict([(item['defindex'], item) for item in
                        schema['result']['items']])

def getitemsbyname(schema):
    """Return an ordered dictionary of items in the schema where the key is
    item_name for each item"""
    itemsbyname = OrderedDict()
    for item in schema['result']['items']:
        name = item['item_name']
        if (name not in itemsbyname and
           item['defindex'] not in (2007, 2015, 2049)):
            itemsbyname[name] = item

    return itemsbyname

def getattributes(schema):
    """Return a dictionary with each attribute's name as key"""
    return {attribute['name']:attribute for attribute in
            schema['result']['attributes']}

def getparticleeffects(schema):
    """Return a dictionary with each particle effect's id as key"""
    return {effect['id']:effect for effect in
            schema['result']['attribute_controlled_attached_particles']}

def getstoreprices(apikey):
    """Return a dictionary of store prices where the key is defindex for
    each item"""
    url = ('http://api.steampowered.com/ISteamEconomy/GetAssetPrices/v0001/'
           '?key={}&language=en&appid=440&currency=usd'.format(apikey))

    prices = json.loads(urlopen(url).read())['result']['assets']

    return {int(price['name']):price for price in prices}

def getnewstoreprices(storeprices):
    """Return a dictionary of store prices of new items with defindex as key"""
    return {index:price for index, price in storeprices.items()
            if 'New' in price['tags']}

def getmarketprices(itemsbyname):
    """Get market prices from tf2spreadsheet.blogspot.com
    Return a dictionary where the key is defindex and value is a dictionary of
    prices for the item"""
    url = ('https://spreadsheets.google.com/pub'
           '?key=0AnM9vQU7XgF9dFM2cldGZlhweWFEUURQU2pmOGJVMlE&output=csv')
    pricesdata = urlopen(url)

    pricesdict = defaultdict(dict)
    denoms = ['Key', 'Bud', 'Scrap']

    reader = csv.DictReader(pricesdata, fieldnames=['quality', 'class', 'name',
                                                    'price', 'lowprice',
                                                    'notes', 'color'])
    sheet = list(reader)[1:-1]

    for row in sheet:
        name = convertmarketname(row)
        price = filtermarketstring(row['price']).title()
        quality = row['quality']
        lowprice = filtermarketstring(row['lowprice']).title()
        lowquality = 'Unique'

        if name == 'Ghastlier/Ghastlierest Gibus':
            for i in ['Ghastlier','Ghastlierest']:
                hat = row.copy()
                hat['name'] = i + ' Gibus'
                sheet.append(hat)

        elif name == 'Halloween Masks':
            for class_ in getallclasses():
                classmask = row.copy()
                classmask['name'] = class_ + ' Mask'
                sheet.append(classmask)

        elif 'Soldier Medal' in name:
            medal = row.copy()
            medal['name'] = "Gentle Manne's Service Medal"
            medal['quality'] = name.replace('Soldier Medal ','')
            sheet.append(medal)

        elif name in itemsbyname:
            if name.startswith('Gold Botkiller'):
                nongold = row.copy()
                nongold['name'] = name.replace('Gold ','')
                nongold['price'] = lowprice
                nongold['lowprice'] = lowprice = ''
                sheet.append(nongold)

            index = itemsbyname[name]['defindex']

            if 'dirty' in row['name']:
                quality += ' (Dirty)'

            if 'dirty' in row['lowprice']:
                lowquality += ' (Dirty)'

            if price:
                # Check if price starts with a number and has no denomination
                if not any(d in price for d in denoms) and isprice(price):
                    # Add Refined denomination
                    price += ' Refined'

                pricesdict[index][quality] = price

            if lowprice and lowprice != '-':
                if not any(d in lowprice for d in denoms) and isprice(lowprice):
                    lowprice += ' Refined'

                pricesdict[index][lowquality] = lowprice

    return pricesdict

def getweapontags():
    """Return all weapon tags"""
    return ['primary', 'secondary', 'melee', 'pda', 'pda2', 'building']

def getalltags():
    """Return all item tags"""
    return (['hat', 'weapon', 'misc', 'tool', 'action',
             'taunt', 'paint', 'token', 'bundle'] + getweapontags())

def getallclasses():
    """Return an OrderedDict of TF2 classes with name as key and
    a list of aliases as value"""
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

    return (str(round(storeprices[index]['prices']['USD']/100.00, 2))
            if index in storeprices else  '')

def getmarketprice(item, marketprices):
    """Get market price of item"""
    index = item['defindex']
    return marketprices[index] if index in marketprices else {}

def getitemattributes(item, allattributes, effects):
    """Get attributes of item"""
    attributelist = []
    if 'attributes' in item:
        attributes = item['attributes']
        for a in attributes:
            value = a['value']

            attribute = allattributes[a['name']]
            if not attribute['hidden'] and 'description_string' in attribute:
                description = attribute['description_string']
                descformat = attribute['description_format']

                if descformat == 'value_is_particle_index':
                    value = effects[value]['name']
                    description = description.replace('%s1','{}')
                else:
                    if descformat == 'value_is_percentage':
                        value = (value * 100) - 100

                    elif descformat == 'value_is_inverted_percentage':
                        value = 100 - (value * 100)

                    elif descformat == 'value_is_additive_percentage':
                        value *= 100

                    description = description.replace('%s1','{:g}')

                description = description.format(value)

                attrdict = {'description':description,
                            'type':attribute['effect_type']}
                attributelist.append(attrdict)

    order = ['neutral', 'positive', 'negative']

    return sorted(attributelist, key=lambda k: order.index(k['type']))

def getitemclasses(item):
    """Get the TF2 classes that can use this item"""
    return (sorted(item['used_by_classes'],
                  key=getallclasses().keys().index)
                  if 'used_by_classes' in item else [])

def getitemtags(item):
    """Get a list of tags that describe the item"""
    tags = []
    itemclass = item['item_class']

    if itemclass == 'bundle':
        tags.append(itemclass)
    elif itemclass.endswith('_token'):
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

def filtermarketstring(string):
    """Clean up a string from the spreadsheet"""
    return string.replace('(clean)','').replace('(dirty)','').strip()

def convertmarketname(row):
    """Changes the market name to match the proper TF2 name"""
    name = filtermarketstring(row['name'])
    repl = {'Meet the Medic':'Taunt: The Meet the Medic',
            'High-Five':'Taunt: The High Five!',
            'Schadenfreude':'Taunt: The Schadenfreude',
            'Enemies Gibbed':'Strange Part: Gib Kills',
            "HHH's Axe":"Horseless Headless Horsemann's Headtaker",
            'Unusual Haunted Metal scrap':'Haunted Metal Scrap',
            'Hazmat Headcase':'HazMat Headcase',
            'Spine-Chilling Skull 2010':'Spine-Chilling Skull',
            'Color No. 216-190-216 (Pink)':'Color No. 216-190-216',
            "Zephaniah's Greed":"Zepheniah's Greed",
            'Bolgan Helmet':'Bolgan',
            'Full Head of Steam':'Full Head Of Steam',
            'Detective Noir':u'Détective Noir',
            'Helmet Without A Home':'Helmet Without a Home',
            'Dueling mini game':'Dueling Mini-Game',
            'Submachine Gun':'SMG',
            'Monoculus':'MONOCULUS!',
            'The Milkman':'Milkman',
            'Superfan':'The Superfan',
            'Athletic Supporter':'The Athletic Supporter',
            'Essential Accessories':'The Essential Accessories',
            "Dr. Grordbert's Copper Crest":"Dr. Grordbort's Copper Crest",
            "Dr. Grordbert's Silver Crest":"Dr. Grordbort's Silver Crest",
            'Key': 'Mann Co. Supply Crate Key',

            'Mann Co. Supply Crate (series 40)':
            'Salvaged Mann Co. Supply Crate',

            'Mann Co. Supply Crate (series 48)':
            'Fall Crate',

            "Lord Cockswain's Novelty Pipe and Mutton Chops":
            "Lord Cockswain's Novelty Mutton Chops and Pipe",

            "Color of a Gentlemann's Business Pants":
            "The Color of a Gentlemann's Business Pants"}

    if name in repl:
        name = repl[name]
    elif row['quality'] == 'Strange Part':
        name = 'Strange Part: ' + name
    elif row['class'] == 'Noisemaker':
        name = 'Noise Maker - ' + name

    return name