"""A module for parsing a query and searching for TF2 items
It supports class based search, eg: 'engineer hats'
It also supports alias based search, eg: 'engi hats'
Regular search, eg: 'Meet the Medic'
Slot search, eg: 'primary weps'
Set search, eg: 'the saharan spy set'
Price search, eg: 'unique > 1 ref hat'
Price visualization, eg: '2.66 ref'
Price conversion, eg: '1.5 keys to ref'
Requires TF2 API module to get items and prices.

Note: You must provide your own image URLs for paint cans and blueprints.
      Replace the relative URLs in createitemdict and _parseblueprints.

"""
import re
import json
from fractions import Fraction
from collections import namedtuple, defaultdict, OrderedDict

import tf2api


DENOMREGEX = (r'((?:earb|b)uds?|'
              'keys?|'
              'ref(?:ined|s)?|'
              'rec(?:laimed|s)?|'
              'scraps?|'
              'wea?p(?:on)?s?)')

PRICEREGEX = (r'(?:(\d+(?:\.\d+)?) ?{})'.format(DENOMREGEX))

QUALITYREGEX = r'({}|collector|collectors|dirty|uncraft(?:able)?)'.format(
    '|'.join(i.lower() for i in tf2api.getallqualities().values()))


def gettf2info(apikey, backpackkey, tradekey, blueprintsfilename):
    """Return a named tuple which contains information from multiple sources
    about TF2 items"""
    schema = tf2api.getschema(apikey)

    items = tf2api.getitems(schema)
    itemsbyname = tf2api.getitemsbyname(schema)
    itemsets = tf2api.getitemsets(schema)
    attributes = tf2api.getattributes(schema)
    effects = tf2api.getparticleeffects(schema)
    itemsets = tf2api.getitemsets(schema)

    storeprices = tf2api.getstoreprices(apikey)
    newstoreprices = tf2api.getnewstoreprices(storeprices)
    bundles = tf2api.getbundles(apikey, storeprices)

    backpackprices = tf2api.getbackpackprices(backpackkey, items, itemsbyname)
    tradeprices = tf2api.gettradeprices(tradekey, items, itemsbyname)

    with open(blueprintsfilename, encoding='utf-8') as f:
        data = json.loads(f.read())
    blueprints = _parseblueprints(data, itemsbyname)

    fields = ('items itemsbyname itemsets attributes effects '
              'blueprints storeprices newstoreprices bundles '
              'backpackprices tradeprices')

    TF2Info = namedtuple('TF2Info', fields)

    return TF2Info(items, itemsbyname, itemsets, attributes, effects,
                   blueprints, storeprices, newstoreprices, bundles,
                   backpackprices, tradeprices)


def getitemsdict(tf2info):
    """Return an ordered dictionary with index as key and itemdict as value"""
    itemsdict = OrderedDict()
    for idx in tf2info.items:
        itemsdict[idx] = createitemdict(idx, tf2info)
    return itemsdict


def search(query, itemsdict, nametoindexmap, itemsets, bundles, pricesource):
    """This function parses the query using parseinput and gets all the
    items that match it. It returns a list of dicts obtained from
    getsearchresult"""
    input_ = parseinput(query)
    query = input_['query']
    querylist = input_['querylist']
    classes = input_['classes']
    tags = input_['tags']

    if not querylist:
        return []

    # Check if searching for an item set
    itemsetmatch = re.match(r'(.+) [sS]et$', query)

    # Check if searching by price
    # Matches this - {quality}{{criteria}{amount}{denom}} {classes|tags}
    pricematch = re.match(r'{}?(?: ?(<|>|=)? ?{})?((?: [a-z]+)*)$'.format(
        QUALITYREGEX, PRICEREGEX), query.lower()) if query else None

    # Get classes and tags in price search, if any
    if pricematch:
        words = pricematch.group(5)
        priceinput = parseinput(words or '')
        priceclasses, pricetags = priceinput['classes'], priceinput['tags']
        if priceclasses or pricetags:
            results = _classtagsearch(priceclasses, pricetags, itemsdict)
        elif words:
            pricematch = None

    # Check if searching for specific indexes
    indexmatch = re.match(r'\d+( \d+)*$', query)
    indexes = query.split() if indexmatch else []

    if classes or tags:
        results = _classtagsearch(classes, tags, itemsdict)

    elif query == 'sets':
        # Get all the item sets and their items
        results = _itemsetsearch(None, itemsets, nametoindexmap, itemsdict)

    elif itemsetmatch:
        # Search for a particular item set or bundle and list its items
        query = itemsetmatch.group(1).lower()
        result = _bundlesearch(query, bundles, nametoindexmap, itemsdict)
        if not result:
            result = _itemsetsearch(query, itemsets, nametoindexmap, itemsdict)

        results = [result] if result else []

    elif pricematch:
        quality = (pricematch.group(1) or 'unique').capitalize()
        criteria = pricematch.group(2)
        amount = pricematch.group(3)
        if amount:
            amount = float(amount)
        denom = _getdenom(pricematch.group(4) or '')

        if priceclasses or pricetags:
            title = results[0]['title'] if results else None
        else:
            title = None
            results = [getsearchresult(items=itemsdict.values())]

        _pricefilter(quality, criteria, amount, denom, results, pricesource)

        if results and title:
            results[0]['title'] = '{} — {}'.format(results[0]['title'], title)

    elif len(indexes) > 1:
        # Searching for specific indexes
        items = []
        for index in indexes:
            index = int(index)
            if index in itemsdict:
                items.append(itemsdict[index])

        results = [getsearchresult(items=items)] if items else []

    else:
        # Regular word search
        result = _wordsearch(query, querylist, itemsdict)
        results = [result] if result else []

        # Check if there's a match between an item set name and query
        results.extend(_itemsetsearch(querylist, itemsets,
                                      nametoindexmap, itemsdict))

    return results


def visualizeprice(query, itemsdict, pricesource):
    """Return a list of items representing a price if parsed from the query"""
    query = parseinput(query)['query']
    pricevizmatch = re.match(
        r'{}(?: (?:in|to) {})?$'.format(PRICEREGEX, DENOMREGEX),
        query.lower())

    if pricevizmatch:
        amount = pricevizmatch.group(1)
        denom = _getdenom(pricevizmatch.group(2))
        todenom = _getdenom(pricevizmatch.group(3) or '')

        items = _getpriceasitems(amount, denom, todenom,
                                 itemsdict, pricesource)

        titlelist = [_getpricestring(item['count'], item['denom'])
                     for item in items]

        title = ' + '.join(titlelist)

        if not (len(items) == 1 and denom == items[0]['denom']):
            title = '{} = {}'.format(_getpricestring(float(amount), denom),
                                     title)

        return [getsearchresult(title, 'price', items)] if items else []


def createitemdict(index, tf2info):
    """Take a TF2 item and return a custom dict with a limited number of
    keys that are used for search"""
    item = tf2info.items[index]
    name = item['item_name']
    classes = tf2api.getitemclasses(item)
    attributes = tf2api.getitemattributes(item,
                                          tf2info.attributes, tf2info.effects)

    storeprice = tf2api.getstoreprice(item, tf2info.storeprices)
    backpackprice = tf2api.getmarketprice(item, tf2info.backpackprices)
    tradeprice = tf2api.getmarketprice(item, tf2info.tradeprices)

    tags = tf2api.getitemtags(item)
    # Sort blueprints by crafting chance
    blueprint = sorted(tf2info.blueprints[index],
                       key=lambda k: k['chance'], reverse=True)

    description = ''
    if 'bundle' in tags and storeprice:
        descriptions = tf2info.bundles[index]['descriptions']
        text = []
        items = []

        for i in range(len(descriptions)):
            key = str(i)
            value = descriptions[key]['value']
            if value in tf2info.itemsbyname:
                items.append(value)
            else:
                text.append(value)

        description = '{}---{}'.format('\n'.join(text), '\n'.join(items))

    elif 'item_description' in item:
        description = item['item_description']
        if 'bundle' in tags and name in tf2info.itemsets:
            description += '---' + '\n'.join(tf2info.itemsets[name]['items'])

    levels = OrderedDict.fromkeys(
        str(item[i]) for i in ('min_ilevel', 'max_ilevel'))
    level = 'Level {} {}'.format('-'.join(levels), item['item_type_name'])

    itemdict = {'index': index,
                'name': name,
                'image': item['image_url'],
                'image_large': item['image_url_large'],
                'description': description,
                'level': level,
                'attributes': attributes,
                'classes': classes,
                'tags': tags,
                'storeprice': storeprice,
                'marketprice': {'backpack.tf': backpackprice,
                                'trade.tf': tradeprice},
                'blueprints': blueprint}

    if 'paint' in tags:
        paintvalue = item['attributes'][0]['value']
        # Ignore Paint Tool
        if paintvalue != 0:
            itemdict['image'] = itemdict['image_large'] = (
                '/images/paints/Paint_Can_{}.png'.format(paintvalue))

    return itemdict


def getsearchresult(title='', type='', items=None):
    """Return a dict containing a group of items used for search results"""
    return {'title': title, 'type': type, 'items': items or []}


def getclasstagtitle(classes, tags):
    """Return a title desciribing a class/tag search"""
    all_classes = list(tf2api.getallclasses().keys())
    classes_text = ', '.join(sorted(classes, key=all_classes.index))
    tags_text = ', '.join(sorted(tags)).title()

    if len(classes) == 1 and len(tags) == 1:
        title = f'{classes_text} {tags_text}'
    elif classes and tags:
        title = f'{classes_text} × {tags_text}'
    elif classes:
        title = classes_text
    elif tags:
        title = tags_text

    return title


def isvalidresult(itemdict, strict=True):
    """Check if item has an image, is not a duplicate and is not bundle junk.
    If strict is True, competition medals also return False"""
    index = itemdict['index']
    duplicates = tf2api.getobsoleteindexes()
    isvalid = (itemdict['image'] and
               index not in duplicates and
               not itemdict['name'].startswith('TF_Bundle'))
    if strict:
        isvalid = (isvalid and 'tournament' not in itemdict['tags'])

    return isvalid


def parseinput(query):
    """Parse a search query and return a dict to be used in search function"""
    classes = set()
    tags = set()

    query = query.strip()

    if query.startswith('"') and query.endswith('"'):
        querylist = [query.strip('"')]
        query = ''
    else:
        querylist = [i for i in _splitspecial(foldaccents(query)) if i not in
                     ('the', 'a', 'of', 's')]

        for word in querylist:
            class_ = _getclass(word)
            tag = _gettag(word)

            if class_:
                classes.add(class_)
            elif tag:
                tags.add(tag)

        # Simple check to differentiate between word and class/tag search
        # Avoids conflicts such as 'meet the medic taunt'
        if (len(tags) + len(classes)) != len(querylist):
            classes = tags = set()

    return {'query': query, 'querylist': querylist,
            'classes': classes, 'tags': tags}


def foldaccents(string):
    """Fold accents in a string"""
    return (string.replace('ä', 'a')
                  .replace('é', 'e')
                  .replace('ò', 'o')
                  .replace('ü', 'u')
                  .replace('Ü', 'U'))


def _classtagsearch(classes, tags, itemsdict):
    """Search for items that match classes and tags"""
    results = defaultdict(list)
    names = set()

    title = getclasstagtitle(classes, tags)

    titles = [title, 'Multi-Class Items', 'All-Class Items']

    # Check if the user is searching for tournament medals
    hidemedals = 'tournament' not in tags
    # Check if the weapon tag is specified (eg. primary, melee)
    hasweapontag = not tags.isdisjoint(tf2api.getweapontags())

    for itemdict in itemsdict.values():
        itemclasses = itemdict['classes']
        itemtags = itemdict['tags']
        # Gives a match if there's an intersection between the item's
        # classes and the parsed classes in the query. Also gives a match
        # if the item doesn't have any classes specified (all-class item)
        isclassmatch = (not classes.isdisjoint(itemclasses) or
                        not itemclasses)
        if hasweapontag:
            # This avoids showing slot tokens when searching for
            # 'primary weapon', 'melee weapon', etc.
            istagmatch = tags.issubset(itemtags)
        else:
            istagmatch = not tags.isdisjoint(itemtags)

        if (isclassmatch or not classes) and (istagmatch or not tags):
            name = itemdict['name']
            # Don't show tournament medals unless explicitly searched
            if isvalidresult(itemdict, hidemedals) and name not in names:
                if len(itemclasses) == 1:
                    results[titles[0]].append(itemdict)
                elif len(itemclasses) > 1:
                    results[titles[1]].append(itemdict)
                else:
                    results[titles[2]].append(itemdict)
                names.add(name)

    results = [getsearchresult(title, items=items)
               for title, items in results.items()]

    results.sort(key=lambda k: titles.index(k['title']))

    return results


def _wordsearch(query, querylist, itemsdict):
    """Search for items whose names match query"""
    items = []
    names = set()

    if query:
        querylist = set(querylist + _pluralize(querylist))
    else:
        pattern = r'\b{}\b'.format(querylist[0])

    for itemdict in itemsdict.values():
        name = foldaccents(itemdict['name'])

        if query:
            wordmatch = not querylist.isdisjoint(_splitspecial(name))
        else:
            wordmatch = (re.search(pattern, name) or
                         re.search(pattern, name.lower()))

        stringmatch = (len(query) > 2 and
                       (query in name or query in name.lower()))

        match = wordmatch or stringmatch

        if match and isvalidresult(itemdict, False):
            if name not in names:
                items.append(itemdict)
                names.add(name)

    if items:
        return getsearchresult(
            items=_getsorteditemlist(items, querylist, query))


def _bundlesearch(query, bundles, nametoindexmap, itemsdict):
    """Search for bundles which match query"""
    for bundle in bundles.values():
        if bundle['name'].lower() == query:
            items = _getbundleitems(bundle, nametoindexmap, itemsdict)
            return getsearchresult(bundle['name'], 'bundle', items)


def _itemsetsearch(query, itemsets, nametoindexmap, itemsdict):
    """Search for item sets whose names match query"""
    results = []
    getall = True

    if query is None:
        isresult = lambda name: True
    elif type(query) == list:
        isresult = lambda name: not set(_splitspecial(name)).isdisjoint(query)
    else:
        isresult = lambda name: name.lower() == query
        getall = False

    for setname, itemset in itemsets.items():
        if isresult(setname):
            items = _getsetitems(itemset, nametoindexmap, itemsdict)
            result = getsearchresult(setname, 'set', items)
            if getall:
                results.append(result)
            else:
                return result

    if getall:
        return results


def _pricefilter(quality, criteria, amount, denom, results, pricesource):
    """Search for items by price based on criteria"""
    getall = amount is None

    if quality in ('Collector', 'Collectors'):
        quality = "Collector's"

    if quality in ('Uncraft', 'Dirty'):
        quality = 'Uncraftable'

    results[0]['title'] = '{}: {} {}'.format(
        quality, criteria or '',
        _getpricestring(amount, denom) if not getall else 'Any')

    for idx, result in enumerate(results):
        items = []
        for itemdict in result['items']:
            price = itemdict['marketprice'][pricesource]

            if quality not in price:
                continue
            elif getall:
                items.append(itemdict)
                continue

            price = price[quality]

            p = price.split()
            valuelow = float(p[0])
            valuehigh = float(p[2]) if len(p) == 4 else valuelow
            pricedenom = p[-1].rstrip('s').replace('Bud', 'Earbuds')

            if denom != pricedenom:
                continue

            if criteria == '<':
                match = valuelow < amount or valuehigh < amount
            elif criteria == '>':
                match = valuelow > amount or valuehigh > amount
            else:
                match = valuelow == amount or valuehigh == amount

            if match:
                items.append(itemdict)

        if items:
            results[idx]['items'] = items
        else:
            results[idx] = None

    results[:] = [result for result in results if result]


def _getsetitems(itemset, nametoindexmap, itemsdict):
    """Get a list of the items in an item set"""
    setitems = []
    for name in itemset['items']:
        name = (name.replace('The ', '')
                    .replace("Capone's Capper", "Capo's Capper")
                    .replace('Conspiratorial Cut', 'Cranial Conspiracy')
                    .replace('Hundekopf', 'Hundkopf')
                    .replace('Skinless Slashers', 'Scaly Scrapers')
                    .replace('Transylvanian Toupe', 'Transylvania Top'))

        setitems.append(itemsdict[nametoindexmap[name]])

    return setitems


def _getbundleitems(bundle, nametoindexmap, itemsdict):
    """Get a list of the items in a bundle"""
    bundleitems = []
    descriptions = bundle['descriptions']

    for i in range(len(descriptions)):
        key = str(i)
        value = descriptions[key]['value']
        if value in nametoindexmap:
            bundleitems.append(itemsdict[nametoindexmap[value]])

    return bundleitems


def _getsorteditemlist(itemslist, querylist, query):
    """Return sorted itemlist based on the intersection between the
    search query words and each item's name. Items without a word intersection
    are sorted based on where the query is found in their names."""
    key = lambda k: (len(set(querylist).intersection(_splitspecial(k['name'])))
                     or -k['name'].lower().find(query.lower()))

    return sorted(itemslist,
                  key=key,
                  reverse=True)


def _getpriceasitems(amount, denom, todenom, itemsdict, pricesource):
    """Return a list of itemdicts that visualize a given price and a dict
    with the count of each item."""
    items = []

    amount = _correctprice(amount, denom)

    denomtoidx = tf2api.getalldenoms()
    denoms = tuple(denomtoidx.keys())
    denomtable = _getdenomvalues(itemsdict, pricesource)

    if todenom:
        amount *= denomtable[denom][todenom]
    else:
        todenom = denom
        # Move to the highest possible denomination
        for d in denoms:
            value = amount * denomtable[denom][d]
            if value >= 1:
                amount = value
                todenom = d
                break

    if amount <= 4000:
        denomidx = denoms.index(todenom)
        # Get count of each denomination and add items to results
        for i, d in enumerate(denoms[denomidx:], denomidx):
            count = int(round(amount, 10))

            if count:
                items.append({'item': itemsdict[denomtoidx[d]],
                              'denom': d,
                              'count': count})

            if i + 1 < len(denoms):
                amount = (amount - count) * denomtable[d][denoms[i + 1]]

    return items


def _getpricestring(amount, denom):
    """Return a human-readable price string"""
    return '{:g} {}'.format(
        amount,
        denom + 's' if denom in ('Key', 'Weapon') and amount != 1 else denom)


def _getdenomvalues(itemsdict, pricesource):
    """Return a mapping to convert between denominations"""
    denomtoidx = tf2api.getalldenoms()
    denoms = tuple(denomtoidx.keys())

    getprice = lambda denom: _correctprice(
        itemsdict[denomtoidx[denom]]['marketprice'][pricesource]['Unique']
        .split()[0], denoms[denoms.index(denom) + 1])

    table = {'Earbuds': {'Key': getprice('Earbuds')},
             'Key': {'Refined': getprice('Key')},
             'Refined': {'Reclaimed': 3.0},
             'Reclaimed': {'Scrap': 3.0},
             'Scrap': {'Weapon': 2.0},
             'Weapon': {}}

    def fill(from_, to=None, value=1):
        if to is None:
            to = from_

        table[from_][to] = value
        table[to][from_] = 1 / value

        if denoms.index(to) + 1 < len(denoms):
            next_ = denoms[denoms.index(to) + 1]
            fill(from_, next_, value * table[to][next_])

    for denom in denoms:
        fill(denom)

    return table


def _correctprice(amount, denom):
    limits = {'Refined': 18, 'Reclaimed': 6, 'Scrap': 2, 'Weapon': 1}

    if denom in limits:
        if '.' in amount:
            count, fraction = amount.split('.')
            # Check if it's a repeating decimal
            if len(fraction) > 1 and len(set(fraction)) == 1:
                # Increase precision
                amount = '.'.join([count, fraction[0] * 4])
        amount = Fraction(amount).limit_denominator(limits[denom])
    else:
        amount = float(amount)

    return amount


def _pluralize(wordlist):
    """Take a list of words and return a list of their plurals"""
    return [i + 's' for i in wordlist]


def _splitspecial(string):
    """Convert a string to lowercase and split it at special characters"""
    return [i for i in re.split(r'\W+', string.lower()) if i]


def _getclass(word):
    """Parse a word and return TF2 class or alias if it matches one"""
    word = word.capitalize()
    for name, aliases in tf2api.getallclasses().items():
        if word == name or word in aliases:
            return name


def _gettag(word):
    """Parse a word and return an item tag if it matches one"""
    weapon = ('wep', 'weap')

    if word in ('watch', 'watches'):
        return 'pda2'
    elif word in weapon or word in _pluralize(weapon):
        return 'weapon'

    for tag in tf2api.getalltags():
        if word in (tag, tag + 's'):
            return tag


def _getdenom(word):
    """Parse a word and return a price denomination if it matches one"""
    denomslist = ('bud', 'key', 'ref', 'rec', 'scrap', 'we')
    denoms = dict(zip(denomslist, tf2api.getalldenoms().keys()))

    hasdenom = re.search('|'.join(denomslist), word.lower())
    if hasdenom:
        return denoms[hasdenom.group(0)]


def _parseblueprints(blueprints, itemsbyname):
    """Parse a dictionary of blueprint descriptions"""
    url = '/images/items/'
    localrepl = {'Any Class Token': 'class_token.png',
                 'Any Slot Token': 'slot_token.png',
                 'Any Token': 'token.png'}

    repl = {"Any Santa's Little Accomplice Weapon":
            "Santa's Little Accomplice Bundle",

            'Any Primary Weapon': 'Rocket Launcher',
            'Any Secondary Weapon': 'Pistol',
            'Any Melee Weapon': 'Fire Axe',
            'Any Spy Watch': 'Invis Watch',
            'Any Hat': 'Modest Pile of Hat',
            'Any Burned Item': 'Burned Banana Peel',
            'Any Cursed Object': 'Voodoo-Cursed Object'}

    polyweps = ("The Gas Jockey's Gear", "The Saharan Spy", "The Tank Buster",
                "The Croc-o-Style Kit", "The Special Delivery")

    for class_ in tf2api.getallclasses():
        repl['Any {} Weapon'.format(class_)] = '{} Starter Pack'.format(class_)

    for name in polyweps:
        repl['Any {} Weapon'.format(name)] = name

    for i in ('Victory', 'Moonman', 'Brainiac'):
        pack = "Dr. Grordbort's {} Pack".format(i)
        repl["Any {} Weapon".format(pack)] = pack

    blueprintsdict = defaultdict(list)
    for b in blueprints:
        required = blueprints[b][0]
        results = blueprints[b][1]

        for name in results:
            if name in itemsbyname:
                index = itemsbyname[name]['defindex']
                chance = int(round(100.0 / len(results)))

                blueprintlist = []

                for i in OrderedDict.fromkeys(required):
                    blueprintdict = {}

                    if i in localrepl:
                        image = url + localrepl[i]

                    elif i in repl:
                        image = itemsbyname[repl[i]]['image_url']

                    elif i in itemsbyname:
                        item = itemsbyname[i]
                        image = item['image_url']

                        blueprintdict['index'] = item['defindex']

                    else:
                        image = '/images/items/whatsthis.png'

                    blueprintdict['name'] = i
                    blueprintdict['image'] = image
                    blueprintdict['count'] = required.count(i)

                    blueprintlist.append(blueprintdict)

                blueprintsdict[index].append({'chance': chance,
                                              'required': blueprintlist})

    return blueprintsdict
