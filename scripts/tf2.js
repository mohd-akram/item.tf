// Generated by CoffeeScript 1.6.3
(function() {
  var HoverBox, Item, ItemBox, User, ajax, capitalize, escapeHTML, getCookie, postAjax, priceSources, root, setCookie, _getAjaxRequest,
    __indexOf = [].indexOf || function(item) { for (var i = 0, l = this.length; i < l; i++) { if (i in this && this[i] === item) return i; } return -1; },
    __bind = function(fn, me){ return function(){ return fn.apply(me, arguments); }; };

  root = typeof exports !== "undefined" && exports !== null ? exports : this;

  priceSources = ['backpack.tf', 'spreadsheet'];

  User = (function() {
    function User() {
      this.id = getCookie('steam_id');
      this.loggedIn = Boolean(this.id);
      Object.defineProperties(this, {
        priceSource: {
          get: function() {
            return getCookie('price_source') || priceSources[0];
          },
          set: function(source) {
            return setCookie('price_source', source, 365);
          }
        }
      });
    }

    User.prototype.isOwnPage = function() {
      var _ref;
      return this.loggedIn && this.id === ((_ref = document.getElementById('steamid')) != null ? _ref.getAttribute('data-id') : void 0);
    };

    return User;

  })();

  Item = (function() {
    function Item(elem) {
      var price, source, _i, _len, _ref, _ref1, _ref2;
      this.elem = elem;
      this.name = elem.title;
      this.id = elem.getAttribute('data-index');
      this.imageUrl = elem.getAttribute('data-image');
      this.description = elem.getAttribute('data-description') || '';
      this.level = elem.getAttribute('data-level');
      this.attributes = ((_ref = elem.getElementsByTagName('div')) != null ? (_ref1 = _ref[0]) != null ? _ref1.innerHTML : void 0 : void 0) || '';
      this.classes = (elem.getAttribute('data-classes') || '').split(',');
      this.tags = (elem.getAttribute('data-tags') || '').split(',');
      this.storePrice = elem.getAttribute('data-storeprice');
      this.blueprints = elem.getElementsByTagName('ul');
      this.prices = {};
      for (_i = 0, _len = priceSources.length; _i < _len; _i++) {
        source = priceSources[_i];
        price = JSON.parse(this.elem.getAttribute("data-" + source));
        if (price) {
          this.prices[source] = price;
        }
      }
      this.wishIndex = elem.getAttribute('data-i');
      this.qualityNo = (_ref2 = elem.className.match(/quality-(\d+)/)) != null ? _ref2[1] : void 0;
    }

    Item.prototype.remove = function() {
      return this.elem.parentNode.removeChild(this.elem);
    };

    return Item;

  })();

  ItemBox = (function() {
    function ItemBox(showLink) {
      this.showLink = showLink != null ? showLink : true;
      this.elem = document.createElement('div');
      this.elem.id = 'itembox';
      document.getElementsByTagName('body')[0].appendChild(this.elem);
    }

    ItemBox.prototype.show = function(elem) {
      this.item = new Item(elem);
      this.source = user.priceSource;
      this._generate();
      return this.elem.style.display = 'block';
    };

    ItemBox.prototype.hide = function() {
      return this.elem.style.display = 'none';
    };

    ItemBox.prototype._nextPriceSource = function() {
      return this.source = priceSources[(priceSources.indexOf(this.source) + 1) % priceSources.length];
    };

    ItemBox.prototype._tagsHTML = function() {
      var html, i, image, isToken, isWeapon, title, _i, _j, _len, _len1, _ref, _ref1, _ref2, _ref3, _ref4, _ref5;
      if (this.item.tags.length) {
        html = '<div id="tags">';
        isWeapon = __indexOf.call(this.item.tags, 'weapon') >= 0;
        isToken = __indexOf.call(this.item.tags, 'token') >= 0;
        _ref = ['primary', 'secondary', 'melee', 'pda2'];
        for (_i = 0, _len = _ref.length; _i < _len; _i++) {
          i = _ref[_i];
          if (__indexOf.call(this.item.tags, i) >= 0) {
            if (isWeapon) {
              _ref1 = ["" + (capitalize(i)) + " Weapon", i], title = _ref1[0], image = _ref1[1];
            } else if (isToken) {
              _ref2 = ['Slot Token', 'slot-token'], title = _ref2[0], image = _ref2[1];
            }
          }
        }
        _ref3 = ['hat', 'misc', 'tool', 'bundle'];
        for (_j = 0, _len1 = _ref3.length; _j < _len1; _j++) {
          i = _ref3[_j];
          if (__indexOf.call(this.item.tags, i) >= 0) {
            _ref4 = [capitalize(i), i], title = _ref4[0], image = _ref4[1];
          }
        }
        if (isToken && this.item.classes.length) {
          _ref5 = ['Class Token', 'class-token'], title = _ref5[0], image = _ref5[1];
        }
        if ((title != null) && (image != null)) {
          html += "<a href=\"/search?q=" + (encodeURIComponent(title)) + "\"\n target=\"_blank\" title=\"" + title + "\" class=\"" + image + "\"></a>";
        }
        return html += '</div>';
      } else {
        return '';
      }
    };

    ItemBox.prototype._nameHTML = function() {
      var html;
      html = this.item.name;
      if (this.showLink) {
        html = "<a href=\"/item/" + this.item.id + "\"\n target=\"_blank\" class=\"glow\" title=\"Go to Item Page\">" + html + "</a>";
      }
      return html = "<h2 id='itemname'>" + html + "</h2>";
    };

    ItemBox.prototype._classesHTML = function() {
      var html, i, _i, _len, _ref;
      if (this.item.classes.length) {
        html = '<div id="classes">';
        _ref = this.item.classes;
        for (_i = 0, _len = _ref.length; _i < _len; _i++) {
          i = _ref[_i];
          html += "<a href=\"/search?q=" + i + "\" target=\"_blank\"\n title=\"" + i + "\" class=\"" + (i.toLowerCase()) + "\"></a>";
        }
        return html += '</div>';
      } else {
        return '';
      }
    };

    ItemBox.prototype._bundleHTML = function() {
      if (__indexOf.call(this.item.tags, 'bundle') >= 0 && this.item.description.indexOf('---') !== -1) {
        return "<a href=\"/search?q=" + (encodeURIComponent(this.item.name)) + "%20Set\"\n target=\"_blank\">\n<div class=\"rounded glow\" style=\"display: inline-block; padding: 7px\">\nView items\n</div>\n</a>";
      } else {
        return '';
      }
    };

    ItemBox.prototype._priceSourceHTML = function() {
      var classifiedsURL, denom, denomMatch, html, price, quality, _ref;
      html = '';
      if (!this.item.prices[this.source]) {
        this._nextPriceSource();
      }
      if (this.item.prices[this.source]) {
        if (this.source === 'backpack.tf') {
          classifiedsURL = "http://backpack.tf/ajax/search_generate.php?defindex=" + this.item.id + "&appid=440&redir=classifieds";
          html += "<a href=\"" + classifiedsURL + "\" class=\"rounded-tight glow\"\n target=\"_blank\" style=\"color: rgb(129, 170, 197)\">\nClassifieds</a><br>";
        }
        _ref = this.item.prices[this.source];
        for (quality in _ref) {
          price = _ref[quality];
          denomMatch = price.match(/(Refined|Key(s)?|Bud(s)?)/);
          if (denomMatch) {
            denom = denomMatch[0];
            price = price.replace(/(\d+(\.\d+)?)/g, "<a href=\"/search?q=\$1%20" + denom + "\"\n target=\"_blank\" class=\"glow\">\$1</a>");
          }
          html += "<span class='" + (quality.toLowerCase()) + "'>" + quality + "</span>: " + price + "<br>";
        }
      }
      return html;
    };

    ItemBox.prototype._pricesHTML = function() {
      var html;
      html = this._priceSourceHTML();
      if (html) {
        return "<div id='marketprice'><span id='pricesource'>" + (capitalize(this.source)) + "</span><h3 id='prices'>" + html + "</h3></div>";
      } else {
        return '';
      }
    };

    ItemBox.prototype._blueprintsHTML = function() {
      var b, chance, html, i, index, j, listItem, name, style, url, _i, _j, _k, _len, _len1, _ref, _ref1, _ref2;
      if (this.item.blueprints.length) {
        html = '<div id="blueprints">';
        _ref = this.item.blueprints;
        for (_i = 0, _len = _ref.length; _i < _len; _i++) {
          b = _ref[_i];
          chance = b.getAttribute('data-chance');
          html += '<div class="blueprint">';
          _ref1 = b.getElementsByTagName('li');
          for (_j = 0, _len1 = _ref1.length; _j < _len1; _j++) {
            i = _ref1[_j];
            for (j = _k = 0, _ref2 = i.getAttribute('data-count'); 0 <= _ref2 ? _k < _ref2 : _k > _ref2; j = 0 <= _ref2 ? ++_k : --_k) {
              name = i.title;
              index = i.getAttribute('data-index');
              style = "background-image: url(" + (i.getAttribute('data-image')) + ")";
              listItem = "<div title=\"" + name + "\" class='item-small' style='" + style + "'></div>";
              if (index) {
                url = "/item/" + index;
              } else {
                name = name.replace('Any ', '').replace('Spy Watch', 'PDA2 Weapon');
                if (name.split(' ').length > 2) {
                  name = name.replace('Weapon', 'Set');
                }
                url = "/search?q=" + (encodeURIComponent(name));
              }
              html += "<a href=\"" + url + "\" target='_blank'>" + listItem + "</a>";
            }
          }
          html += "<div title=\"Crafting Chance\" style=\"position: absolute; right: 10px\">\n<h3>" + chance + "%</h3></div></div>";
        }
        return html += '</div>';
      } else {
        return '';
      }
    };

    ItemBox.prototype._outpostHTML = function() {
      return "<a href=\"#\" id=\"find-trades-btn\"\n class=\"icon-exchange icon-large button-icon\" title=\"Find Trades\"></a>\n\n<form name=\"tf2outpostform\" method=\"POST\" style=\"display: inline-block\"\n action=\"http://www.tf2outpost.com/search\">\n\n<input type=\"hidden\" name=\"json\">\n<input type=\"hidden\" name=\"type\" value=\"any\">\n<input type=\"submit\" name=\"submit\" value=\"Search\" style=\"display: none\">\n\n<select id=\"tradetype\" class=\"textbox\">\n  <option value=\"has1\">Want</option>\n  <option value=\"wants1\">Have</option>\n</select>\n\n<select id=\"quality\" class=\"textbox\">\n  <option value=\"6\">Unique</option>\n  <option value=\"3\">Vintage</option>\n  <option value=\"11\">Strange</option>\n  <option value=\"1\">Genuine</option>\n  <option value=\"13\">Haunted</option>\n  <option value=\"5\">Unusual</option>\n</select>\n\n</form>";
    };

    ItemBox.prototype._wishlistHTML = function() {
      if (user.loggedIn) {
        return "<div style=\"display: inline-block; width: 40px\">\n<div id=\"wishlistmessage\"\n style=\"display: none; margin: 0 0 4px -18px\">Added</div>\n<i id=\"wishlistbutton\" class=\"button-icon rounded icon-star icon-large\"\n style=\"background-color: transparent\"\n title=\"Add to Wishlist\"></i>\n</div>";
      } else {
        return '';
      }
    };

    ItemBox.prototype._buttonsHTML = function() {
      var wikiLink;
      wikiLink = "http://wiki.teamfortress.com/wiki/" + (encodeURIComponent(this.item.name));
      return "<div id=\"buttons\">\n\n<a class=\"icon-info icon-large button-icon\" target=\"_blank\"\n title=\"Open in Wiki\" href=\"" + wikiLink + "\"></a>\n\n<a class=\"icon-shopping-cart icon-large button-icon\"\n target=\"_blank\" title=\"Community Market\"\n href=\"http://steamcommunity.com/market/search?q=appid%3A440%20" + (encodeURIComponent(this.item.name)) + "\"></a>\n\n" + (this._outpostHTML()) + "\n" + (this._wishlistHTML()) + "\n</div>";
    };

    ItemBox.prototype._buyHTML = function() {
      if (this.item.storePrice) {
        return "<div id=\"buy\">\n<form style=\"display: inline-block\">$" + this.item.storePrice + "<br>\n<input type=\"text\" value=\"1\" size=\"1\" id=\"quantity\"\n class=\"textbox\" style=\"text-align: right\">\n</form><a href=\"#\" id=\"buybutton\"></a></div>";
      } else {
        return '';
      }
    };

    ItemBox.prototype._pricesLink = function() {
      var button, prices,
        _this = this;
      button = document.getElementById('pricesource');
      prices = document.getElementById('prices');
      if (button && Object.keys(this.item.prices).length > 1) {
        button.style.cursor = 'pointer';
        button.onclick = function() {
          _this._nextPriceSource();
          button.innerHTML = capitalize(_this.source);
          return prices.innerHTML = _this._priceSourceHTML();
        };
        button.onmouseover = function() {
          return button.style.textShadow = '0 0 10px rgb(196, 241, 128)';
        };
        return button.onmouseout = function() {
          return button.style.textShadow = '';
        };
      }
    };

    ItemBox.prototype._outpostLink = function() {
      var _this = this;
      if (window.navigator.userAgent.indexOf('Valve Steam GameOverlay') === -1) {
        this.form.target = '_blank';
      }
      return document.getElementById('find-trades-btn').onclick = function(event) {
        var tradeType;
        tradeType = document.getElementById('tradetype').value;
        _this.form.json.value = "{\"filters\":{},\"" + tradeType + "\":\"440," + _this.item.id + "," + _this.form.quality.value + "\"}";
        return _this.form.submit.click();
      };
    };

    ItemBox.prototype._wishlistLink = function() {
      var action, button, idx, wish, _i, _len, _ref,
        _this = this;
      if (user.isOwnPage()) {
        _ref = document.getElementsByClassName('item');
        for (idx = _i = 0, _len = _ref.length; _i < _len; idx = ++_i) {
          wish = _ref[idx];
          if (wish.getAttribute('data-i') === this.item.wishIndex) {
            this.item.wishIndex = idx.toString();
            break;
          }
        }
      }
      if (user.loggedIn) {
        action = '/wishlist/add';
        button = document.getElementById('wishlistbutton');
        if (user.isOwnPage()) {
          action = '/wishlist/remove';
          button.title = 'Remove from Wishlist';
        }
        return button.onclick = function() {
          var data;
          data = {
            'index': _this.item.id,
            'quality': _this.form.quality.value
          };
          if (user.isOwnPage()) {
            data = {
              'i': _this.item.wishIndex
            };
          }
          return postAjax(action, data, function(response) {
            var message;
            if (response === 'Added') {
              message = document.getElementById('wishlistmessage');
              message.style.display = 'block';
              message.className = 'animated fadeInLeft';
              return setTimeout((function() {
                return message.className = 'animated fadeOut';
              }), 1000);
            } else if (response === 'Removed') {
              _this.hide();
              return _this.item.remove();
            }
          });
        };
      }
    };

    ItemBox.prototype._buyLink = function() {
      var button,
        _this = this;
      button = document.getElementById('buybutton');
      if (button) {
        return button.onclick = function() {
          var quantity;
          quantity = document.getElementById('quantity').value;
          return window.open("http://store.steampowered.com/buyitem/440/" + _this.item.id + "/" + quantity);
        };
      }
    };

    ItemBox.prototype._generate = function() {
      var hoverArea, i, option, _i, _len, _ref, _results;
      this.elem.innerHTML = "" + (this._tagsHTML()) + (this._nameHTML()) + (this._classesHTML()) + "\n" + (this._bundleHTML()) + "\n" + (this._pricesHTML()) + "\n" + (this._blueprintsHTML()) + "\n" + (this._buttonsHTML()) + (this._buyHTML());
      this.form = document.tf2outpostform;
      this._pricesLink();
      this._outpostLink();
      this._wishlistLink();
      this._buyLink();
      hoverArea = this.item.elem.cloneNode(true);
      hoverArea.id = 'hoverarea';
      hoverArea.className = '';
      hoverArea.setAttribute('style', "background-image: url(" + this.item.imageUrl + ")");
      this.elem.insertBefore(hoverArea, document.getElementById('blueprints') || document.getElementById('buttons'));
      new HoverBox(hoverArea);
      if (this.item.qualityNo) {
        return this.form.quality.value = this.item.qualityNo;
      } else if (this.item.prices[this.source]) {
        _ref = this.form.quality.options;
        _results = [];
        for (i = _i = 0, _len = _ref.length; _i < _len; i = ++_i) {
          option = _ref[i];
          if (option.innerHTML in this.item.prices[this.source]) {
            this.form.quality.selectedIndex = i;
            break;
          } else {
            _results.push(void 0);
          }
        }
        return _results;
      }
    };

    return ItemBox;

  })();

  HoverBox = (function() {
    function HoverBox(arg) {
      this._clickItem = __bind(this._clickItem, this);
      this._moveMouse = __bind(this._moveMouse, this);
      this._hideItemBox = __bind(this._hideItemBox, this);
      this._hide = __bind(this._hide, this);
      this._show = __bind(this._show, this);
      var area;
      if (arg instanceof ItemBox) {
        this.itemBox = arg;
      }
      if (this.itemBox == null) {
        area = arg;
      }
      this.elem = document.getElementById('hoverbox');
      if (!this.elem) {
        this.elem = document.createElement('div');
        this.elem.id = 'hoverbox';
        document.getElementsByTagName('body')[0].appendChild(this.elem);
      }
      this._add(area);
    }

    HoverBox.prototype._add = function(area) {
      var item, list, _i, _len,
        _this = this;
      list = area ? [area] : document.getElementsByClassName('item');
      for (_i = 0, _len = list.length; _i < _len; _i++) {
        item = list[_i];
        item.addEventListener("mouseout", this._hide, false);
        item.addEventListener("mousemove", this._moveMouse, false);
        item.addEventListener("mouseover", this._show, false);
        if (this.itemBox != null) {
          item.addEventListener("click", this._clickItem, false);
        }
      }
      if (this.itemBox != null) {
        document.getElementsByTagName('body')[0].addEventListener("click", this._hideItemBox, false);
        return document.onkeydown = function(e) {
          if (e.keyCode === 27) {
            return _this.itemBox.hide();
          }
        };
      }
    };

    HoverBox.prototype._show = function(e) {
      var descList, description, item;
      item = new Item(e.target);
      description = escapeHTML(item.description);
      if (description) {
        if (__indexOf.call(item.tags, 'bundle') >= 0 && description.indexOf('---') !== -1) {
          descList = description.split('---');
          description = "" + descList[0] + "\n<span style=\"color: #95af0c\">" + descList[1] + "</span>";
        }
        description = "<br>" + description;
      }
      this.elem.innerHTML = "<div style=\"font-size: 1.2em; color: rgb(230, 230, 230)\">" + item.name + "</div><span style=\"color: gray\">" + item.level + "</span>" + item.attributes + description;
      return this.elem.style.display = 'block';
    };

    HoverBox.prototype._hide = function() {
      return this.elem.style.display = 'none';
    };

    HoverBox.prototype._hideItemBox = function(e) {
      var el, els, _ref;
      el = e.target;
      if (el.className !== 'item') {
        els = [];
        while (el) {
          els.push(el);
          el = el.parentNode;
        }
        if (_ref = this.itemBox.elem, __indexOf.call(els, _ref) < 0) {
          return this.itemBox.hide();
        }
      }
    };

    HoverBox.prototype._moveMouse = function(e) {
      this.elem.style.top = "" + (e.pageY + 28) + "px";
      return this.elem.style.left = "" + (e.pageX - 154) + "px";
    };

    HoverBox.prototype._clickItem = function(e) {
      this.itemBox.show(e.target);
      e.preventDefault();
      return e.stopPropagation();
    };

    return HoverBox;

  })();

  capitalize = function(word) {
    return word[0].toUpperCase() + word.slice(1);
  };

  escapeHTML = function(string) {
    return string.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  };

  getCookie = function(name) {
    var cookie, cookies, _i, _len;
    cookies = document.cookie.split(';');
    for (_i = 0, _len = cookies.length; _i < _len; _i++) {
      cookie = cookies[_i];
      while (cookie[0] === ' ') {
        cookie = cookie.slice(1);
      }
      if (cookie.slice(0, name.length) === name) {
        return cookie.slice(name.length + 1);
      }
    }
  };

  setCookie = function(name, value, days) {
    var date, expires;
    expires = '';
    if (days) {
      date = new Date;
      date.setDate(date.getDate() + days);
      expires = ";expires=" + (date.toUTCString());
    }
    return document.cookie = "" + name + "=" + value + expires;
  };

  ajax = function(url, callback) {
    var request;
    request = _getAjaxRequest(callback);
    request.open('GET', url, true);
    request.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    return request.send();
  };

  postAjax = function(url, data, callback) {
    var name, request, value;
    request = _getAjaxRequest(callback);
    request.open('POST', url, true);
    request.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    return request.send(((function() {
      var _results;
      _results = [];
      for (name in data) {
        value = data[name];
        _results.push("" + name + "=" + value);
      }
      return _results;
    })()).join('&'));
  };

  _getAjaxRequest = function(callback) {
    var request;
    request = new XMLHttpRequest;
    request.onreadystatechange = function() {
      if (request.readyState === 4 && request.status === 200) {
        return callback(request.responseText);
      }
    };
    return request;
  };

  root.user = new User;

  root.ItemBox = ItemBox;

  root.HoverBox = HoverBox;

}).call(this);

/*
//@ sourceMappingURL=tf2.map
*/
