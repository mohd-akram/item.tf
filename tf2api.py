"""This module is based on the Steam WebAPI and can be used to get information
about items in TF2. Using this module, you can obtain the item schema,
store prices, bundles, item sets and attributes for TF2.
You can also obtain market prices from backpack.tf.

There are also functions for parsing the information of each item.

"""
import asyncio
import json
from collections import defaultdict, OrderedDict

import aiohttp


async def getschema(apikey):
    """Return the schema"""
    schema_task = asyncio.ensure_future(_getschemaoverview(apikey))

    all_items = []

    start = 0
    while start is not None:
        items, start = await _getschemaitems(apikey, start)
        all_items.extend(items)

    schema = await schema_task
    schema['result']['items'] = all_items

    return schema


async def _getschemaoverview(apikey):
    url = ('https://api.steampowered.com/IEconItems_440/GetSchemaOverview/v1/'
           f'?key={apikey}&language=en')
    return await _getjsonresponse(url)


async def _getschemaitems(apikey, start):
    url = ('https://api.steampowered.com/IEconItems_440/GetSchemaItems/v1/'
           f'?key={apikey}&language=en&start={start}')
    result = (await _getjsonresponse(url))['result']
    return result['items'], result.get('next')


async def getitemsinfo(apikey, storeprices, indexes):
    """Return a dictionary of AssetClassInfo values with defindex as key"""
    url = ('https://api.steampowered.com/ISteamEconomy/GetAssetClassInfo/v0001/'
           '?key={0}&language=en&appid=440&class_count={1}'.format(apikey,
                                                                   len(indexes)
                                                                   ))

    for n, index in enumerate(indexes):
        classid = storeprices[index]['classid']
        url += '&classid{0}={1}'.format(n, classid)

    infobyid = (await _getjsonresponse(url))['result']
    del infobyid['success']

    return {int(iteminfo['app_data']['def_index']): iteminfo
            for iteminfo in infobyid.values()}


async def getbundles(apikey, storeprices):
    """Return a dictionary of store bundles with defindex as key"""
    indexes = [index for index, price in storeprices.items()
               if not {'Bundles', 'Class_Bundles'}.isdisjoint(price['tags'])]
    return await getitemsinfo(apikey, storeprices, indexes)


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


async def getstoreprices(apikey):
    """Return a dictionary of store prices where the key is defindex for
    each item"""
    url = ('https://api.steampowered.com/ISteamEconomy/GetAssetPrices/v0001/'
           '?key={}&language=en&appid=440&currency=usd'.format(apikey))

    prices = (await _getjsonresponse(url))['result']['assets']

    return {int(price['name']): price for price in prices}


def getnewstoreprices(storeprices):
    """Return a dictionary of store prices of new items with defindex as key"""
    return {index: price for index, price in storeprices.items()
            if 'New' in price['tags']}


async def getbackpackprices(apikey, items, itemsbyname):
    """Get market prices from backpack.tf.
    Return a dictionary where the key is defindex and value is a dictionary of
    prices for the item"""
    url = ('https://backpack.tf/api/IGetPrices/v4/'
           '?key={}&compress=1'.format(apikey))

    pricesdata = (await _getjsonresponse(url))['response']['items']

    pricesdict = defaultdict(dict)

    qualities = getallqualities()

    denoms = {'metal': 'Refined', 'hat': 'Hat', 'keys': 'Key', 'usd': 'USD'}

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


def getweapontags():
    """Return all weapon tags"""
    return ('primary', 'secondary', 'melee', 'pda', 'pda2', 'building')


def getalltags():
    """Return all item tags"""
    return (('weapon', 'cosmetic', 'hat', 'misc', 'taunt', 'tool', 'action',
             'paint', 'craft', 'token', 'bundle', 'tournament', 'halloween') +
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
    return OrderedDict([('Key', 5021),
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

    if item.get('holiday_restriction') == 'halloween_or_fullmoon':
        tags.append('halloween')

    return tags


def getobsoleteindexes():
    """Return the indexes of obsolete items that have newer versions"""
    map_stamps = {
        2007, 2015, 2049, 2079, 2123, 2125, 2138, 2139, 2140, 2143, 2155, 2156
    }
    starter_packs = set(range(2018, 2027)) | set(range(2094, 2103))
    return {699, 2093} | map_stamps | starter_packs


async def getplayerbackpack(apikey, steamid):
    """Return the player backpack of the given steamid"""
    url = ('https://api.steampowered.com/IEconItems_440/GetPlayerItems/v0001/'
           f'?key={apikey}&steamid={steamid}')
    return (await _getjsonresponse(url)).get('result')


async def getplayersummary(apikey, steamid):
    """Return the player summary of the given steamid"""
    return (await getplayersummaries(apikey, [steamid]))[0]


async def getplayersummaries(apikey, steamids):
    """Return the player summaries of a list of steamids"""
    url = ('https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/'
           f"?key={apikey}&steamids={','.join(steamids)}")

    return (await _getjsonresponse(url))['response']['players']


async def resolvevanityurl(apikey, vanityurl):
    """Return the steamid of a given vanity url"""
    url = ('https://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/'
           f'?key={apikey}&vanityurl={vanityurl}')

    response = (await _getjsonresponse(url))['response']
    if response['success'] == 1:
        return response['steamid']


async def _getjsonresponse(url):
    headers = {'User-Agent': 'tf2api'}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as response:
            return json.loads((await response.read()).decode())
