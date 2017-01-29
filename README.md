item.tf
=======

This is a Sanic site that lets you search TF2 items and find the ones you
want. There are two main ways to search - you can either use regular keyword
search or search by classes and item tags (eg. weapon, misc, hat, etc.). Once
you find an item you want, you can get all kinds of information about it such
as its store price, market price and crafting recipes to help you obtain it.
You can also search for item sets or view a list of them by typing 'sets'.

Get Started
-----------

Copy config.default.py to config.py and fill in your API keys in the file.

Run this command to install dependencies.

    pip install -r requirements.txt

You'll also need to install the [Redis server](http://redis.io/download).

Run updatestore.py to update the Redis cache. Then, simply launch main.py.

Hosting
-------

To host the site in FreeBSD 11, first clone into `/usr/local/www/item.tf`.
Then, run the following as root:

    pkg install -y nginx redis
    mkdir -p /usr/local/etc/rc.conf.d
    echo 'nginx_enable="YES"' > /usr/local/etc/rc.conf.d/nginx
    echo 'redis_enable="YES"' > /usr/local/etc/rc.conf.d/redis
    cd /usr/local/www/item.tf
    make install

Make sure you set the `ssl_certificate` and `ssl_certificate_key` directives
and have `include sites/item.tf;` at the end of the `http` block in
`/usr/local/etc/nginx/nginx.conf`.

Structure
---------

There are three main files:

 * main.py - Contains the page handlers
 * tf2api.py - Contains the main functions for getting items, store prices,
   market prices and other information.
 * tf2search.py - Contains the parsing and search functions.

TF2 API
-------
tf2api.py (depends on aiohttp) was designed to be used either for this project
or separately. It contains many helpful functions to get information about
items in TF2.

Example:
```python
>>> import tf2api
>>> schema = tf2api.getschema(apikey)
>>> items = tf2api.getitems(schema)
>>> itemsbyname = tf2api.getitemsbyname(schema)

>>> pan = items[264] # 264 is the defindex of the item, Or:
>>> pan = itemsbyname['Frying Pan']

>>> tf2api.getitemclasses(pan)
['Scout', 'Soldier', 'Pyro', 'Demoman', 'Heavy', 'Medic', 'Sniper']

>>> tf2api.getitemtags(pan)
['weapon', 'melee']
```

Thanks
------
This project was inspired by and depends on the great TF2 community to
function, so a special thanks to the following:

[Backpack.tf](http://backpack.tf)

[Trade.tf](http://trade.tf)

[TF2 Outpost](http://tf2outpost.com)

[TF2 Crafting Advisor](http://tf2crafting.info)

[TF2B](http://tf2b.com)
