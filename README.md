TF2 Find
========

This is a Google App Engine site that lets you search TF2 items and find the ones you want. There are two main ways to search - you can either use regular keyword search or search by classes and item tags (eg. weapon, misc, hat, etc.). Once you find an item you want, you can get all kinds of information about it such as its store price, market price and crafting recipes to help you obtain it. You can also search for item sets or view a list of them by typing 'sets'.

Get Started
-----------

Rename config.default.py to config.py and fill in your API keys in the file. Then, simply add the directory to the Google App Engine Launcher and start the server.

Structure
---------

There are three main files:

 * tf2.py - Contains the page handlers
 * tf2api.py - Contains the main functions for getting items, store prices, market prices (tf2spreadsheet.blogspot.com) and other information.
 * tf2search.py - Contains the parsing and search functions.

TF2 API
-------
tf2api.py has no dependencies and was designed to be used either for this project or separately. It contains many helpful functions to get information about items in TF2.

Example:
```python
>>> import tf2api
>>> schema = tf2api.getschema(apikey)
>>> items = tf2api.getitems(schema)
>>> itemsbyname = tf2api.getitemsbyname(schema)

>>> pan = items[264] # 264 is the defindex of the item, Or:
>>> pan = itemsbyname['Frying Pan']

>>> tf2api.getitemclasses(pan)
[u'Scout', u'Soldier', u'Pyro', u'Demoman', u'Heavy', u'Medic', u'Sniper']

>>> tf2api.getitemtags(pan)
['weapon', u'melee']
```

Dependencies
------------
There are no external dependencies, only built-in Python modules.

Tested with Python 2.7.

Thanks
------
This project was inspired by and depends on the great TF2 community to function, so a special thanks to the following:

[TF2 Spreadsheet](http://tf2spreadsheet.traderempire.com)

[Backpack.tf](http://backpack.tf)

[Trade.tf](http://trade.tf)

[TF2 Outpost](http://tf2outpost.com)

[TF2 Crafting Advisor](http://tf2crafting.info)

[TF2B](http://tf2b.com)
