
# coding: utf-8

"""This module is based on the Steam WebAPI and can be used to get information
about items in TF2. Using this module, you can obtain the item schema,
store prices, bundles, item sets and attributes for TF2.
You can also obtain market prices from the community spreadsheet.

There are also functions for parsing the information of each item.

"""
import json
import re
from urllib2 import urlopen, build_opener
from HTMLParser import HTMLParser
from collections import defaultdict, OrderedDict


def getschema(apikey, timeout=30):
    """Return the schema"""
    url = ('http://api.steampowered.com/IEconItems_440/GetSchema/v0001/'
           '?key={}&language=en'.format(apikey))

    return json.loads(urlopen(url, timeout=timeout).read())


def getitemsinfo(apikey, storeprices, indexes, timeout=30):
    """Return a dictionary of AssetClassInfo values with defindex as key"""
    url = ('http://api.steampowered.com/ISteamEconomy/GetAssetClassInfo/v0001/'
           '?key={0}&language=en&appid=440&class_count={1}'.format(apikey,
                                                                   len(indexes)
                                                                   ))

    idtoindex = {}
    for n, index in enumerate(indexes):
        classid = storeprices[index]['classid']
        idtoindex[classid] = index
        url += '&classid{0}={1}'.format(n, classid)

    infobyid = json.loads(urlopen(url, timeout=timeout).read())['result']
    del infobyid['success']

    return {idtoindex[classid]: iteminfo for classid, iteminfo in
            infobyid.items()}


def getbundles(apikey, storeprices):
    """Return a dictionary of store bundles with defindex as key"""
    indexes = [index for index, price in storeprices.items()
               if 'Bundles' in price['tags']]
    return getitemsinfo(apikey, storeprices, indexes)


def getitemsets(schema):
    """Return a dictionary of itemsets with 'name' as key"""
    return {itemset['name']: itemset for itemset in
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
    duplicates = getobsoleteindexes()

    for item in schema['result']['items']:
        name = item['item_name']
        if name not in itemsbyname:
            if item['defindex'] not in duplicates:
                itemsbyname[name] = item

    return itemsbyname


def getattributes(schema):
    """Return a dictionary with each attribute's name as key"""
    return {attribute['name']: attribute for attribute in
            schema['result']['attributes']}


def getparticleeffects(schema):
    """Return a dictionary with each particle effect's id as key"""
    return {effect['id']: effect for effect in
            schema['result']['attribute_controlled_attached_particles']}


def getstoreprices(apikey, timeout=30):
    """Return a dictionary of store prices where the key is defindex for
    each item"""
    url = ('http://api.steampowered.com/ISteamEconomy/GetAssetPrices/v0001/'
           '?key={}&language=en&appid=440&currency=usd'.format(apikey))

    prices = json.loads(urlopen(url,
                                timeout=timeout).read())['result']['assets']

    return {int(price['name']): price for price in prices}


def getnewstoreprices(storeprices):
    """Return a dictionary of store prices of new items with defindex as key"""
    return {index: price for index, price in storeprices.items()
            if 'New' in price['tags']}


def getspreadsheetprices(itemsbyname, timeout=30):
    """Get market prices from TF2 Spreadsheet.
    Return a dictionary where the key is defindex and value is a dictionary of
    prices for the item"""
    url = 'http://tf2spreadsheet.traderempire.com/spreadsheet/text/'

    opener = build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    data = opener.open(url, timeout=timeout).read()

    parser = _SpreadsheetParser()
    parser.feed(data)
    pricesdata = parser.prices.items()

    botkillers = ['Gold', 'Silver', 'Blood', 'Rust', 'Diamond', 'Carbonado']

    pricesdict = {}

    for name, prices in pricesdata:
        name = _convertmarketname(name)

        if name in itemsbyname:
            index = itemsbyname[name]['defindex']
            pricesdict[index] = prices

        elif name == 'Slot Token':
            for type_ in ['Primary', 'Secondary', 'Melee', 'PDA2']:
                pricesdata.append(('Slot Token - ' + type_, prices))

        elif name == 'Class Token':
            for class_ in getallclasses():
                pricesdata.append(('Class Token - ' + class_, prices))

        elif name == 'Halloween Masks':
            for class_ in getallclasses():
                pricesdata.append((class_ + ' Mask', prices))

        elif 'Mk.I' in name and 'Botkiller' not in name:
            for quality, price in prices.items():
                robothead = re.search('|'.join(botkillers), quality).group(0)
                propername = '{} Botkiller {}'.format(robothead, name)
                pricesdata.append((propername, {'Strange': price}))

    return pricesdict


def getbackpackprices(apikey, items, itemsbyname, timeout=30):
    """Get market prices from backpack.tf.
    Return a dictionary where the key is defindex and value is a dictionary of
    prices for the item"""
    url = ('http://backpack.tf/api/IGetPrices/v3/'
           '?format=json&key={}'.format(apikey))

    pricesdata = json.loads(
        urlopen(url, timeout=timeout).read())['response']['prices']

    pricesdict = defaultdict(dict)
    itemnames = set()

    qualities = {'1': 'Genuine', '3': 'Vintage', '5': 'Unusual', '6': 'Unique',
                 '11': 'Strange', '13': 'Haunted', '600': 'Uncraftable'}

    denoms = {'metal': 'Refined', 'keys': 'Key',
              'earbuds': 'Bud', 'usd': 'USD'}

    for index, prices in pricesdata.items():
        index = int(index)
        name = items[index]['item_name']
        # Backpack.tf uses different indexes. This gets the name of the
        # item from their API and finds its proper index.
        idx = itemsbyname[name]['defindex']

        # Make sure that the proper index is used by not overwriting prices
        # with the correct index
        if index != idx and name in itemnames:
            continue

        for quality, price in prices.items():
            if quality in qualities:
                item = items[index]

                iscrate = False

                if 'attributes' in item and item['attributes']:
                    attribute = item['attributes'][0]
                    if attribute['name'] == 'set supply crate series':
                        iscrate = True
                        crateno = str(int(attribute['value']))

                if '0' in price and (not iscrate or crateno not in price):
                    price = price['0']
                elif iscrate:
                    price = price[crateno]
                else:
                    continue

                price = price['current']

                value = price['value']
                valuehigh = (' - {:g}'.format(price['value_high'])
                             if 'value_high' in price else '')

                denom = denoms[price['currency']]
                qualityname = qualities[quality]

                if value != 1 and denom not in ('Refined', 'USD'):
                    denom += 's'

                itemnames.add(name)
                pricesdict[idx][qualityname] = '{:g}{} {}'.format(value,
                                                                  valuehigh,
                                                                  denom)

    return pricesdict


def getweapontags():
    """Return all weapon tags"""
    return ['primary', 'secondary', 'melee', 'pda', 'pda2', 'building']


def getalltags():
    """Return all item tags"""
    return (['hat', 'weapon', 'misc', 'tool', 'action', 'taunt', 'paint',
             'token', 'bundle', 'tournament'] + getweapontags())


def getallclasses():
    """Return an OrderedDict of TF2 classes with name as key and
    a list of aliases as value"""
    return OrderedDict([('Scout', ['Scoot']),
                        ('Soldier', ['Solly']),
                        ('Pyro', []),
                        ('Demoman', ['Demo']),
                        ('Heavy', ['Hoovy']),
                        ('Engineer', ['Engi', 'Engie']),
                        ('Medic', []),
                        ('Sniper', []),
                        ('Spy', [])])


def getallqualities():
    """Return a dictionary of TF2 item qualities with number as key and
    description as value"""
    return {6: 'Unique',
            3: 'Vintage',
            11: 'Strange',
            1: 'Genuine',
            13: 'Haunted',
            5: 'Unusual'}


def getalldenoms():
    """Return an OrderedDict of price denominations in descending order with
    the defindex of their corresponding items as value"""
    return OrderedDict([('Earbuds', 143),
                        ('Key', 5021),
                        ('Refined', 5002),
                        ('Reclaimed', 5001),
                        ('Scrap', 5000),
                        ('Weapon', 0)])


def getstoreprice(item, storeprices):
    """Get store price of item"""
    index = item['defindex']

    return (str(round(storeprices[index]['prices']['USD'] / 100.00, 2))
            if index in storeprices else '')


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
                    description = description.replace('%s1', '{}')
                else:
                    if descformat == 'value_is_percentage':
                        value = (value * 100) - 100

                    elif descformat == 'value_is_inverted_percentage':
                        value = 100 - (value * 100)

                    elif descformat == 'value_is_additive_percentage':
                        value *= 100

                    description = description.replace('%s1', '{:g}')

                description = description.format(value)

                attrdict = {'description': description,
                            'type': attribute['effect_type']}
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
    itemtypename = item['item_type_name']

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

    if itemtypename == 'Special Taunt':
        tags.append('taunt')

    elif itemtypename == 'Tournament Medal':
        tags.append('tournament')

    if 'tool' in item:
        tags.append('tool')

        if item['tool']['type'] == 'paint_can':
            tags.append('paint')

    return tags


def getobsoleteindexes():
    """Return the indexes of obsolete items that have newer versions"""
    return (699, 2007, 2015, 2049, 2093) + tuple(range(2018, 2027))


def getplayersummary(apikey, steamid):
    """Return the player summary of the given steamid"""
    return getplayersummaries(apikey, [steamid])[0]


def getplayersummaries(apikey, steamids):
    """Return the player summaries of a list of steamids"""
    url = ('http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/'
           '?key={}&steamids='.format(apikey))

    url += ','.join(steamids)
    return json.loads(urlopen(url).read())['response']['players']


def resolvevanityurl(apikey, vanityurl):
    """Return the steamid of a given vanity url"""
    url = ('http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/'
           '?key={}&vanityurl={}'.format(apikey, vanityurl))

    response = json.loads(urlopen(url).read())['response']

    if response['success'] == 1:
        return response['steamid']


def _convertmarketname(name):
    """Changes the market name to match the proper TF2 name"""
    repl = {'Meet the Medic': 'Taunt: The Meet the Medic',
            'Taunt: The High-Five!': 'Taunt: The High Five!',
            'Schadenfreude': 'Taunt: The Schadenfreude',
            'Unusual Haunted Metal': 'Haunted Metal Scrap',
            'Hazmat Headcase': 'HazMat Headcase',
            "Zephaniah's Greed": "Zepheniah's Greed",
            'Full Head of Steam': 'Full Head Of Steam',
            'Claidheamh Mr': 'Claidheamh Mòr',
            'Detective Noir': 'Détective Noir',
            'QuÃ¤ckenbirdt': 'Quäckenbirdt',
            'Brutal Bouffant': 'Brütal Bouffant',
            'Helmet Without A Home': 'Helmet Without a Home',
            'Dueling mini game': 'Dueling Mini-Game',
            'Monoculus': 'MONOCULUS!',
            'The Milkman': 'Milkman',
            'The Triple A Badge': 'Triple A Badge',
            'Superfan': 'The Superfan',
            'Athletic Supporter': 'The Athletic Supporter',
            'Essential Accessories': 'The Essential Accessories',
            'Koto': 'Noise Maker - Koto',
            'Winter Holiday': 'Noise Maker - Winter Holiday',
            # Halloween 2012
            'Voodoo Juju (Slight Return)': 'Voodoo JuJu (Slight Return)',
            'Halloween Kills': 'Strange Part: Halloween Kills',
            'Die Job (halloween spell)': 'Halloween Spell: Die Job',

            'Sinister Staining (halloween spell)':
            'Halloween Spell: Sinister Staining',

            'Chromatic Corruption (halloween spell)':
            'Halloween Spell: Chromatic Corruption',

            'Salvaged Mann Co. Supply Crate (series 50)':
            'Salvaged Mann Co. Supply Crate',

            'Strange Part: Kills While Ubercharged':
            'Strange Part: Kills While Übercharged',

            "Lord Cockswain's Novelty Pipe and Mutton Chops":
            "Lord Cockswain's Novelty Mutton Chops and Pipe",

            "Color of a Gentlemann's Business Pants":
            "The Color of a Gentlemann's Business Pants"}

    if name in repl:
        name = repl[name]

    return name.decode('utf-8')


class _SpreadsheetParser(HTMLParser):
    """A class to parse the TF2 Spreadsheet website"""
    def __init__(self):
        HTMLParser.__init__(self)
        self.name = None
        self.isname = False
        self.prices = defaultdict(dict)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if 'class' in attrs:
            class_ = attrs['class']

            if tag == 'td' and class_ == 'tf2-ss-c10':
                self.isname = True

            elif tag == 'div' and class_.startswith('tf2-ss-quality'):
                title = str(attrs['title'].replace(u'\u2013', '-').title())
                quality, price = title.split('\r')

                quality = quality.replace('(Dirty)', 'Uncraftable')

                isrefined = not any(i in price for i in ['Bud', 'Key'])

                if price[0].isdigit() and isrefined:
                    price += ' Refined'

                self.prices[self.name][quality] = price

    def handle_data(self, data):
        if self.isname:
            self.name = data
            self.isname = False
