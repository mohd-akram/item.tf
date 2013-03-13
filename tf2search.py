
# coding: utf-8

"""A module for parsing a query and searching for TF2 items
It supports class based search, eg: 'engineer hats'
It also supports alias based search, eg: 'engi hats'
Regular search, eg: 'Meet the Medic'
Slot search, eg: 'primary weps'
Set search, eg: 'the saharan spy set'
Requires TF2 API module to get items and prices.

Note: You must provide your own image URLs for paint cans and blueprints.
      Replace the relative URLs in createitemdict and _parseblueprints.

"""
import re
import json
from collections import namedtuple, defaultdict, OrderedDict

import tf2api


def gettf2info(apikey, backpackkey, blueprintsfilename):
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

    spreadsheetprices = tf2api.getspreadsheetprices(itemsbyname)
    backpackprices = tf2api.getbackpackprices(backpackkey, items, itemsbyname)

    with open(blueprintsfilename) as f:
        data = json.loads(f.read().decode('utf-8'))
    blueprints = _parseblueprints(data, itemsbyname)

    fields = ('items itemsbyname itemsets attributes effects '
              'blueprints storeprices newstoreprices bundles '
              'spreadsheetprices backpackprices')

    TF2Info = namedtuple('TF2Info', fields)

    return TF2Info(items, itemsbyname, itemsets, attributes, effects,
                   blueprints, storeprices, newstoreprices, bundles,
                   spreadsheetprices, backpackprices)


def getitemsdict(tf2info):
    """Returns an ordered dictionary with index as key and itemdict as value"""
    itemsdict = OrderedDict()
    for idx in tf2info.items:
        itemsdict[idx] = createitemdict(idx, tf2info)

    return itemsdict


def search(query, itemsdict, nametoindexmap, itemsets, bundles):
    """This method parses the result obtained from _parseinput and gets all the
    items that match this result. It returns a dict with two keys - mainitems,
    and otheritems. The mainitems value is a list for regular results while the
    otheritems value is a dict of lists for several different results"""
    mainitems = []
    otheritems = defaultdict(list)
    names = set()

    result = _parseinput(query)
    query = result['query']
    querylist = result['querylist']
    classes = result['classes']
    tags = result['tags']

    querylength = len(query)

    # Check if searching for an item set
    itemsetmatch = re.match(r'(.+) [sS]et$', query)
    # Check if using price visualization
    pricematch = re.match(r'(\d+(\.\d+)?) '
                          '(([eE]arb|[bB])ud(s)?|'
                          '[rR]ef(ined|s)?|'
                          '[rR]ec(laimed|s)?|'
                          '[kK]ey(s)?|'
                          '[sS]crap)$', query)
    # Check if the weapon tag is specified (eg. primary, melee)
    hasweapontag = not set(tags).isdisjoint(tf2api.getweapontags())
    # Check if the user is searching for tournament medals
    hidemedals = 'tournament' not in tags

    if classes or tags:
        # Search using classes and tags
        for itemdict in itemsdict.values():
            itemclasses = itemdict['classes']
            itemtags = itemdict['tags']
            # Gives a match if there's an intersection between the item's
            # classes and the parsed classes in the query. Also gives a match
            # if the item doesn't have any classes specified (all-class item)
            isclassmatch = (not set(itemclasses).isdisjoint(classes) or
                            not itemclasses)
            if hasweapontag:
                # This avoids showing slot tokens when searching for
                # 'primary weapon', 'melee weapon', etc.
                istagmatch = set(tags).issubset(itemtags)
            else:
                istagmatch = not set(tags).isdisjoint(itemtags)

            if (isclassmatch or not classes) and (istagmatch or not tags):
                name = itemdict['name']
                # Don't show tournament medals unless explicitly searched
                if isvalidresult(itemdict, hidemedals) and name not in names:
                    if len(itemclasses) == 1:
                        mainitems.append(itemdict)
                    elif len(itemclasses) > 1:
                        otheritems['Multi-Class Items'].append(itemdict)
                    else:
                        otheritems['All-Class Items'].append(itemdict)
                    names.add(name)

    elif query == 'all':
        # Get all the items in the schema as is
        mainitems = itemsdict.values()

    elif query == 'sets':
        # Get all the item sets and their items
        for setname, itemset in itemsets.items():
            otheritems[setname].extend(_getsetitems(itemset, nametoindexmap,
                                                    itemsdict))

    elif itemsetmatch:
        # Search for a particular item set or bundle and list its items
        itemsetquery = itemsetmatch.group(1).lower()

        for setname, itemset in itemsets.items():
            if setname.lower() == itemsetquery:
                otheritems[setname].extend(_getsetitems(itemset,
                                                        nametoindexmap,
                                                        itemsdict))
                break
        # Check bundles if nothing found in item sets
        if not otheritems:
            for bundle in bundles.values():
                if bundle['name'].lower() == itemsetquery:
                    bundleitems = _getbundleitems(bundle, nametoindexmap,
                                                  itemsdict)
                    otheritems[bundle['name']].extend(bundleitems)
                    break

    elif pricematch:
        amount = float(pricematch.group(1))
        denom = _getdenom(pricematch.group(3).lower())

        items, counts = _getpriceasitems(amount, denom, itemsdict)

        titlelist = ['{} {}'.format(v, k + 's' if k == 'Key' and v != 1 else k)
                     for k, v in counts.items()]

        title = ' + '.join(titlelist)

        if items:
            otheritems[title].extend(items)

    else:
        # Regular word search
        for itemdict in itemsdict.values():
            name = foldaccents(itemdict['name'])
            namelist = _splitspecial(name)

            wordmatch = not set(namelist).isdisjoint(querylist +
                                                     _pluralize(querylist))

            stringmatch = (querylength > 2 and
                           (query in name or query in name.lower()))

            match = wordmatch or stringmatch

            if match and isvalidresult(itemdict, False):
                if name not in names:
                    mainitems.append(itemdict)
                    names.add(name)

        # Check if there's a match between an item set name and query
        for setname, itemset in itemsets.items():
            if not set(_splitspecial(setname)).isdisjoint(querylist):
                otheritems[setname].extend(_getsetitems(itemset,
                                                        nametoindexmap,
                                                        itemsdict))

        mainitems = _getsorteditemlist(mainitems, querylist, query)

    length = len(mainitems) + sum([len(i) for i in otheritems.values()])

    return {'mainitems': mainitems, 'otheritems': otheritems, 'length': length}


def createitemdict(index, tf2info):
    """Take a TF2 item and return a custom dict with a limited number of
    keys that are used for search"""
    item = tf2info.items[index]
    name = item['item_name']
    classes = tf2api.getitemclasses(item)
    attributes = tf2api.getitemattributes(item,
                                          tf2info.attributes, tf2info.effects)

    storeprice = tf2api.getstoreprice(item, tf2info.storeprices)
    spreadsheetprice = tf2api.getmarketprice(item, tf2info.spreadsheetprices)
    backpackprice = tf2api.getmarketprice(item, tf2info.backpackprices)
    tags = tf2api.getitemtags(item)
    # Sort blueprints by crafting chance
    blueprint = sorted(tf2info.blueprints[index], reverse=True)

    description = ''
    if 'bundle' in tags and storeprice:
        descriptions = tf2info.bundles[index]['descriptions']
        text = []
        items = []

        for i in range(len(descriptions)):
            key = str(i)
            value = descriptions[key]['value']
            if 'color' in descriptions[key] or items:
                items.append(value)
            else:
                text.append(value)

        description = '{0}---{1}'.format('\n'.join(text), '\n'.join(items))

    elif 'item_description' in item:
        description = item['item_description']
        if 'bundle' in tags and name in tf2info.itemsets:
            description += '---' + '\n'.join(tf2info.itemsets[name]['items'])

    itemdict = {'index': index,
                'name': name,
                'image': item['image_url'],
                'image_large': item['image_url_large'],
                'description': description,
                'attributes': attributes,
                'classes': classes,
                'tags': tags,
                'storeprice': storeprice,
                'marketprice': {'spreadsheet': spreadsheetprice,
                                'backpack.tf': backpackprice},
                'blueprints': blueprint}

    if 'paint' in tags:
        paintvalue = str(int(item['attributes'][1]['value']))
        # Ignore Paint Tool
        if paintvalue != '1':
            itemdict['image'] = itemdict['image_large'] = (
                '/images/paints/Paint_Can_{}.png'.format(paintvalue))

    return itemdict


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


def foldaccents(string):
    """Fold accents in a string"""
    return (string.replace(u'ä', 'a')
                  .replace(u'é', 'e')
                  .replace(u'ò', 'o')
                  .replace(u'ü', 'u')
                  .replace(u'Ü', 'U'))


def _getsetitems(itemset, nametoindexmap, itemsdict):
    """Get a list of the items in an item set"""
    setitems = []
    for name in itemset['items']:
        name = name.replace('The ', '').replace("Capone's Capper",
                                                "Capo's Capper")
        setitems.append(itemsdict[nametoindexmap[name]])

    return setitems


def _getbundleitems(bundle, nametoindexmap, itemsdict):
    """Get a list of the items in a bundle"""
    bundleitems = []
    descriptions = bundle['descriptions']

    for i in range(len(descriptions)):
        key = str(i)
        value = descriptions[key]['value']
        if 'color' in descriptions[key] or bundleitems:
            itemnames = [i for i in value.replace(', ', ',').split(',') if i]
            for itemname in itemnames:
                bundleitems.append(itemsdict[nametoindexmap[itemname]])

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


def _getpriceasitems(amount, denom, itemsdict):
    """Return a list of itemdicts that visualize a given price and a dict
    with the count of each item."""
    items = []
    counts = OrderedDict()

    if denom in ('Refined', 'Reclaimed'):
        # Allow common values such as 1.33 and 0.66
        amount += 0.01

    denomtoidx = tf2api.getalldenoms()
    denoms = denomtoidx.keys()

    # Convert denomination to Earbuds
    for i in denoms[:denoms.index(denom)]:
        amount /= _getdenomvalue(i, itemsdict)

    denom = 'Earbuds'

    if amount <= 2000:
        # Get count of each denomination and add items to results
        for i in denoms:
            idx = denomtoidx[i]
            count = int(amount)
            value = _getdenomvalue(i, itemsdict)

            if count:
                items.extend([itemsdict[idx]] * count)
                counts[i] = count

            amount = ((amount - count) * value)

    return items, counts


def _getdenomvalue(denom, itemsdict):
    """Return the value of a given denomination in terms of its lower
    denomination"""
    denomtoidx = tf2api.getalldenoms()

    idx = denomtoidx[denom]

    if denom in ('Earbuds', 'Key'):
        value = float(
            itemsdict[idx]['marketprice']['backpack.tf']['Unique']
            .split()[0])
    elif denom == 'Scrap':
        value = 2
    else:
        value = 3

    return value


def _pluralize(wordlist):
    """Take a list of words and return a list of their plurals"""
    return [i + 's' for i in wordlist]


def _splitspecial(string):
    """Split a string at special characters and convert it to lowercase"""
    return [i for i in re.split(r'\W+', string.lower()) if i]


def _getclass(word):
    """Parse a word and return TF2 class or alias if it matches one"""
    word = word.capitalize()
    for name, aliases in tf2api.getallclasses().items():
        if word == name or word in aliases:
            return name


def _gettag(word):
    """Parse a word and return an item tag if it matches one"""
    weapon = ['wep', 'weap']
    tags = tf2api.getalltags()
    for tag in tags:
        if word in weapon or word in _pluralize(weapon):
            return 'weapon'
        elif word == tag or word == tag + 's':
            return tag


def _getdenom(word):
    """Parse a word and return a price denomination if it matches one"""
    denomslist = ['bud', 'key', 'ref', 'rec', 'scrap']
    denoms = dict(zip(denomslist, tf2api.getalldenoms().keys()))

    hasdenom = re.search('|'.join(denomslist), word)
    if hasdenom:
        return denoms[hasdenom.group(0)]


def _parseinput(query):
    """Parse a search query and return a dict to be used in search function"""
    querylist = [i for i in _splitspecial(foldaccents(query)) if i not in
                 ['the', 'a', 'of', 's']]

    classes = []
    tags = []
    for word in querylist:
        class_ = _getclass(word)
        tag = _gettag(word)

        if class_:
            classes.append(class_)
        elif tag:
            tags.append(tag)

    # Simple check to differentiate between word search and class/tag search
    # Avoids conflicts such as 'meet the medic taunt'
    if (len(tags) + len(classes)) != len(querylist):
        classes = tags = []

    return {'query': query, 'querylist': querylist,
            'classes': classes, 'tags': tags}


def _parseblueprints(blueprints, itemsbyname):
    """Parse a dictionary of blueprint descriptions"""
    url = '/images/items/'
    localrepl = {'Any Class Token': 'class_token.png',
                 'Any Slot Token': 'slot_token.png',
                 'Any Token': 'token.png',
                 'Any Primary Weapon': 'primary.png',
                 'Any Secondary Weapon': 'secondary.png',
                 'Any Melee Weapon': 'melee.png',
                 'Any Spy Watch': 'pda2.png'}

    repl = {"Any Santa's Little Accomplice Weapon":
            "Santa's Little Accomplice Bundle",

            "Any Burned Item": "Burned Banana Peel",
            "Any Cursed Object": "Voodoo-Cursed Object"}

    polyweps = ["The Gas Jockey's Gear", "The Saharan Spy", "The Tank Buster",
                "The Croc-o-Style Kit", "The Special Delivery"]

    for class_ in tf2api.getallclasses():
        repl['Any {} Weapon'.format(class_)] = '{} Starter Pack'.format(class_)

    for name in polyweps:
        repl['Any {} Weapon'.format(name)] = name

    for i in ['Victory', 'Moonman', 'Brainiac']:
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
