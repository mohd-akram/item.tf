"""This module is based on the Steam WebAPI and can be used to get information
about items in TF2. Using this module, you can obtain the item schema,
store prices, bundles, item sets and attributes for TF2.
You can also obtain market prices from backpack.tf and trade.tf.

There are also functions for parsing the information of each item.

"""
import json
from urllib.request import Request, urlopen
from collections import defaultdict, OrderedDict

import aiohttp


def getschema(apikey, timeout=30):
    """Return the schema"""
    url = ('http://api.steampowered.com/IEconItems_440/GetSchema/v0001/'
           '?key={}&language=en'.format(apikey))

    return json.loads(urlopen(url, timeout=timeout).read().decode())


def getitemsinfo(apikey, storeprices, indexes, timeout=30):
    """Return a dictionary of AssetClassInfo values with defindex as key"""
    url = ('http://api.steampowered.com/ISteamEconomy/GetAssetClassInfo/v0001/'
           '?key={0}&language=en&appid=440&class_count={1}'.format(apikey,
                                                                   len(indexes)
                                                                   ))

    for n, index in enumerate(indexes):
        classid = storeprices[index]['classid']
        url += '&classid{0}={1}'.format(n, classid)

    infobyid = json.loads(
        urlopen(url, timeout=timeout).read().decode())['result']
    del infobyid['success']

    return {int(iteminfo['app_data']['def_index']): iteminfo
            for iteminfo in infobyid.values()}


def getbundles(apikey, storeprices):
    """Return a dictionary of store bundles with defindex as key"""
    indexes = [index for index, price in storeprices.items()
               if not {'Bundles', 'Class_Bundles'}.isdisjoint(price['tags'])]
    return getitemsinfo(apikey, storeprices, indexes)


def getitemsets(schema):
    """Return an ordered dictionary of itemsets with 'name' as key"""
    return OrderedDict([(itemset['name'], itemset) for itemset in
                        schema['result']['item_sets']])


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

    prices = json.loads(
        urlopen(url, timeout=timeout).read().decode())['result']['assets']

    return {int(price['name']): price for price in prices}


def getnewstoreprices(storeprices):
    """Return a dictionary of store prices of new items with defindex as key"""
    return {index: price for index, price in storeprices.items()
            if 'New' in price['tags']}


def getbackpackprices(apikey, items, itemsbyname, timeout=30):
    """Get market prices from backpack.tf.
    Return a dictionary where the key is defindex and value is a dictionary of
    prices for the item"""
    url = ('http://backpack.tf/api/IGetPrices/v4/'
           '?key={}&compress=1'.format(apikey))

    r = Request(url, headers={'User-Agent': 'tf2api'})
    pricesdata = json.loads(
        urlopen(r, timeout=timeout).read().decode())['response']['items']

    pricesdict = defaultdict(dict)

    qualities = getallqualities()

    denoms = {'metal': 'Refined', 'hat': 'Hat', 'keys': 'Key',
              'earbuds': 'Bud', 'usd': 'USD'}

    for name, iteminfo in pricesdata.items():
        if name not in itemsbyname:
            continue

        index = itemsbyname[name]['defindex']
        item = items[index]

        iscrate = False

        if 'attributes' in item and item['attributes']:
            attribute = item['attributes'][0]
            if attribute['name'] == 'set supply crate series':
                iscrate = True
                crateno = str(attribute['value'])

        if 'prices' not in iteminfo:
            continue

        for quality, tradeinfo in iteminfo['prices'].items():
            try:
                qualityname = qualities[int(quality)]
            except KeyError:
                continue

            for tradable, craftinfo in tradeinfo.items():
                # Ignore non-tradable version if there is a tradable one
                if tradable == 'Non-Tradable' and 'Tradable' in tradeinfo:
                    continue

                for craftable, price in craftinfo.items():
                    if type(price) is list:
                        price = price[0]
                    else:
                        if iscrate and crateno in price:
                            price = price[crateno]
                        elif '0' in price:
                            price = price['0']
                        else:
                            continue

                    if not price['value']:
                        continue

                    value = price['value']
                    valuehigh = (' - {:g}'.format(price['value_high'])
                                 if 'value_high' in price else '')

                    denom = denoms[price['currency']]

                    if (value != 1 or valuehigh) and denom not in ('Refined',
                                                                   'USD'):
                        denom += 's'

                    qlty = (qualityname if craftable != 'Non-Craftable'
                            else 'Uncraftable')

                    pricesdict[index][qlty] = '{:g}{} {}'.format(
                        value, valuehigh, denom)

    return pricesdict


def gettradeprices(apikey, items, itemsbyname, timeout=30):
    """Get market prices from trade.tf.
    Return a dictionary where the key is defindex and value is a dictionary of
    prices for the item"""
    url = 'http://www.trade.tf/api/spreadsheet.json?key={}'.format(apikey)

    r = Request(url, headers={'User-Agent': 'tf2api'})
    pricesdata = json.loads(
        urlopen(r, timeout=timeout).read().decode())['items']

    pricesdict = defaultdict(dict)
    itemnames = set()
    crates = defaultdict(int)

    qualities = getallqualities()
    qualities[-1] = 'Uncraftable'

    denoms = {'r': 'Refined', 'k': 'Key', 'b': 'Bud'}

    for index, prices in pricesdata.items():
        index = int(index)
        if index not in items:
            # For crates, index = 10000*crate_defindex + crate_number
            crateno = index % 10000
            index //= 10000

            # Store the price of the highest crate number only
            if crateno < crates[index]:
                continue
            else:
                crates[index] = crateno

        name = items[index]['item_name']

        # Trade.tf uses different indexes.
        idx = itemsbyname[name]['defindex']
        if index != idx and name in itemnames:
            continue

        for quality, price in prices.items():
            quality = int(quality)
            if 'regular' not in price:
                continue
            price = price['regular']

            if price['unsure']:
                continue

            value = price['low']
            valuehigh = (' - {:g}'.format(round(price['hi'], 2))
                         if value != price['hi'] else '')

            denom = denoms[price['unit']]
            qualityname = qualities[quality]

            if (value != 1 or valuehigh) and denom != 'Refined':
                denom += 's'

            itemnames.add(name)
            pricesdict[idx][qualityname] = '{:g}{} {}'.format(round(value, 2),
                                                              valuehigh,
                                                              denom)

    return pricesdict


def getweapontags():
    """Return all weapon tags"""
    return ('primary', 'secondary', 'melee', 'pda', 'pda2', 'building')


def getalltags():
    """Return all item tags"""
    return (('weapon', 'cosmetic', 'hat', 'misc', 'tournament',
             'action', 'taunt', 'tool', 'paint', 'craft', 'token', 'bundle') +
            getweapontags())


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
            14: "Collector's",
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

    return ('{:.2f}'.format(storeprices[index]['prices']['USD'] / 100.00)
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

                if attrdict['type'] == 'unusual':
                    attrdict['type'] = 'neutral'

                attributelist.append(attrdict)

    order = ('neutral', 'positive', 'negative')

    return sorted(attributelist, key=lambda k: order.index(k['type']))


def getitemclasses(item):
    """Get the TF2 classes that can use this item"""
    return (sorted(item['used_by_classes'],
            key=list(getallclasses().keys()).index)
            if 'used_by_classes' in item else [])


def getitemtags(item):
    """Get a list of tags that describe the item"""
    tags = []
    itemclass = item['item_class']
    itemtypename = item['item_type_name']

    if itemclass == 'bundle':
        tags.append(itemclass)

    elif itemclass == 'craft_item':
        tags.append('craft')

    elif itemclass.endswith('_token'):
        tags.append('token')

    if 'item_slot' in item:
        slot = item['item_slot']

        if slot in getweapontags() and itemclass != 'slot_token':
            tags.append('weapon')

        if slot == 'misc':
            tags.append('cosmetic')

        if itemtypename in ('#TF_Wearable_Hat', 'Hat', 'Mask',
                            'Holiday Hat', 'Headset', 'Hair'):
            tags.append('hat')
        else:
            tags.append(slot)

    if itemtypename == 'Tournament Medal':
        tags.append('tournament')

    if 'tool' in item:
        tags.append('tool')

        if item['tool']['type'] == 'paint_can':
            tags.append('paint')

    return tags


def getobsoleteindexes():
    """Return the indexes of obsolete items that have newer versions"""
    return ({699, 2007, 2015, 2049, 2079, 2093, 2123, 2125, 2138, 2139} |
            set(range(2018, 2027)))


async def getplayersummary(apikey, steamid):
    """Return the player summary of the given steamid"""
    return (await getplayersummaries(apikey, [steamid]))[0]


async def getplayersummaries(apikey, steamids, timeout=5):
    """Return the player summaries of a list of steamids"""
    url = ('http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/'
           '?key={}&steamids={}'.format(apikey, ','.join(steamids)))

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return json.loads(
                (await response.read()).decode()
            )['response']['players']


async def resolvevanityurl(apikey, vanityurl, timeout=5):
    """Return the steamid of a given vanity url"""
    url = ('http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/'
           '?key={}&vanityurl={}'.format(apikey, vanityurl))

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response = json.loads((await response.read()).decode())['response']
            if response['success'] == 1:
                return response['steamid']
