TF2 Find
========

This is a Google App Engine site that lets you search TF2 items and find the ones you want. It's still in progress, but the main idea is that it you can find everything you need to know about the store price, market price and crafting recipe to help you obtain it. The future plan is to create some sort of recommendation mechanism.

[**Live Demo**](http://tf2find.appspot.com)

Get Started
-----------

Create a file named api_key.txt with your Steam API key in the main directory. Then, simply add the directory to the Google App Engine Launcher and start the server.

Structure
---------

There are three main files:

 * tf2.py - Contains the page handlers
 * tf2api.py - Contains the main functions for getting items, store prices and market prices (tf2spreadsheet.blogspot.com)
 * tf2search.py - Contains the parsing and search functions. It also has a function called createitemdict - this function takes an item, store prices and market prices. It processes them and returns a special dictionary which has all the keys and values about the item that I need to use in the site.

tf2api.py has no dependencies and can be used separately.

Dependencies
------------
There are no external dependencies, only built-in Python modules.

Thanks
------
This project was inspired by and depends on the great TF2 community to function, so a special thanks to the following:

[TF2 Outpost](http://tf2outpost.com)

[TF2 Crafting Advisor](http://tf2crafting.info)

[TF2 Spreadsheet](http://tf2spreadsheet.blogspot.com)

[TF2B](http://tf2b.com)
