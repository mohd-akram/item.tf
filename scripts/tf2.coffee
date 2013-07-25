root = exports ? this

priceSources = ['backpack.tf', 'spreadsheet']

class User
  constructor: ->
    @id = getCookie 'steam_id'
    @loggedIn = Boolean(@id)

    Object.defineProperties @,
      priceSource:
        get: -> getCookie('price_source') or priceSources[0]
        set: (source) -> setCookie 'price_source', source, 365

  isOwnPage: -> @loggedIn and @id is document.getElementById('steamid')
                                            ?.getAttribute('data-id')

class Item
  constructor: (@elem) ->
    @name = elem.title
    @id = elem.getAttribute 'data-index'
    @imageUrl = elem.getAttribute 'data-image'
    @description = elem.getAttribute('data-description') or ''
    @level = elem.getAttribute 'data-level'
    @attributes = elem.getElementsByTagName('div')?[0]?.innerHTML or ''
    @classes = (elem.getAttribute('data-classes') or '').split ','
    @tags = (elem.getAttribute('data-tags') or '').split ','
    @storePrice = elem.getAttribute 'data-storeprice'
    @blueprints = elem.getElementsByTagName 'ul'

    @prices = {}
    for source in priceSources
      price = JSON.parse @elem.getAttribute "data-#{source}"
      @prices[source] = price if price

    @wishIndex = elem.getAttribute 'data-i'
    @qualityNo = elem.className.match(/quality-(\d+)/)?[1]

  remove: -> @elem.parentNode.removeChild @elem

class ItemBox
  constructor: (@showLink=true) ->
    @elem = document.createElement 'div'
    @elem.id = 'itembox'
    document.getElementsByTagName('body')[0].appendChild @elem

  show: (elem) ->
    @item = new Item(elem)
    @source = user.priceSource

    @_generate()
    @elem.style.display = 'block'

  hide: -> @elem.style.display = 'none'

  _nextPriceSource: -> @source =
    priceSources[(priceSources.indexOf(@source) + 1) % priceSources.length]

  _tagsHTML: ->
    if @item.tags.length
      html = '<div id="tags">'
      isWeapon = 'weapon' in @item.tags
      isToken = 'token' in @item.tags

      for i in ['primary', 'secondary', 'melee', 'pda2']
        if i in @item.tags
          if isWeapon
            [title, image] = ["#{capitalize i} Weapon", i]

          else if isToken
            [title, image] = ['Slot Token', 'slot-token']

      for i in ['hat', 'misc', 'tool', 'bundle']
        if i in @item.tags
          [title, image] = [capitalize(i), i]

      if isToken and @item.classes.length
        [title, image] = ['Class Token', 'class-token']

      if title? and image?
        html +=
          """
          <a href="/search?q=#{encodeURIComponent title}"
           target="_blank" title="#{title}" class="#{image}"></a>
          """

      html += '</div>'
    else ''

  _nameHTML: ->
    html = @item.name

    if @showLink
      html =
        """
        <a href="/item/#{@item.id}"
         target="_blank" class="glow" title="Go to Item Page">#{html}</a>
        """
    html = "<h2 id='itemname'>#{html}</h2>"

  _classesHTML: ->
    if @item.classes.length
      html = '<div id="classes">'
      for i in @item.classes
        html +=
          """
          <a href="/search?q=#{i}" target="_blank"
           title="#{i}" class="#{i.toLowerCase()}"></a>
          """
      html += '</div>'
    else ''

  _bundleHTML: ->
    # Link to bundle items HTML
    if 'bundle' in @item.tags and @item.description.indexOf('---') isnt -1
      """
      <a href="/search?q=#{encodeURIComponent @item.name}%20Set"
       target="_blank">
      <div class="rounded glow" style="display: inline-block; padding: 7px">
      View items
      </div>
      </a>
      """
    else ''

  _priceSourceHTML: ->
    html = ''

    if not @item.prices[@source]
      @_nextPriceSource()

    if @item.prices[@source]
      if @source is 'backpack.tf'
        classifiedsURL = "http://backpack.tf/classifieds/search/#{
          encodeURIComponent @item.name}"

        html +=
          """
          <a href="#{classifiedsURL}" class="rounded-tight glow"
           target="_blank" style="color: rgb(129, 170, 197)">
          Classifieds</a><br>
          """

      for quality, price of @item.prices[@source]
        denomMatch = price.match(/(Refined|Key(s)?|Bud(s)?)/)

        if denomMatch
          denom = denomMatch[0]

          price = price.replace(/(\d+(\.\d+)?)/g,
            """
            <a href="/search?q=\$1%20#{denom}"
             target="_blank" class="glow">\$1</a>
            """)
        html += "<span class='#{quality.toLowerCase()}'>#{
          quality}</span>: #{price}<br>"

    return html

  _pricesHTML: ->
    html = @_priceSourceHTML()
    if html then "<div id='marketprice'><span id='pricesource'>#{
      capitalize @source}</span><h3 id='prices'>#{html}</h3></div>" else ''

  _blueprintsHTML: ->
    if @item.blueprints.length
      html = '<div id="blueprints">'
      for b in @item.blueprints
        chance = b.getAttribute 'data-chance'

        html += '<div class="blueprint">'
        for i in b.getElementsByTagName 'li'
          for j in [0...i.getAttribute 'data-count']
            name = i.title
            index = i.getAttribute 'data-index'
            style = "background-image: url(#{i.getAttribute 'data-image'})"

            listItem =  "<div title=\"#{name}\" class='item-small' style='#{
              style}'></div>"

            if index
              url = "/item/#{index}"
            else
              name = name.replace('Any ', '')
                         .replace('Spy Watch', 'PDA2 Weapon')

              if name.split(' ').length > 2
                name = name.replace 'Weapon', 'Set'

              url = "/search?q=#{encodeURIComponent name}"

            html += "<a href=\"#{url}\" target='_blank'>#{listItem}</a>"

        html +=
          """
          <div title="Crafting Chance" style="position: absolute; right: 10px">
          <h3>#{chance}%</h3></div></div>
          """

      html += '</div>'
    else ''

  _outpostHTML: ->
    """
    <a href="#" id="find-trades-btn"
     class="icon-exchange icon-large button-icon" title="Find Trades"></a>

    <form name="tf2outpostform" method="POST" style="display: inline-block"
     action="http://www.tf2outpost.com/search">

    <input type="hidden" name="json">
    <input type="hidden" name="type" value="any">
    <input type="submit" name="submit" value="Search" style="display: none">

    <select id="tradetype" class="textbox">
      <option value="has1">Want</option>
      <option value="wants1">Have</option>
    </select>

    <select id="quality" class="textbox">
      <option value="6">Unique</option>
      <option value="3">Vintage</option>
      <option value="11">Strange</option>
      <option value="1">Genuine</option>
      <option value="13">Haunted</option>
      <option value="5">Unusual</option>
    </select>

    </form>
    """

  _wishlistHTML: ->
    if user.loggedIn
      """
      <div style="display: inline-block; width: 40px">
      <div id="wishlistmessage"
       style="display: none; margin: 0 0 4px -18px">Added</div>
      <i id="wishlistbutton" class="button-icon rounded icon-star icon-large"
       style="background-color: transparent"
       title="Add to Wishlist"></i>
      </div>
      """
    else ''

  _buttonsHTML: ->
    wikiLink = "http://wiki.teamfortress.com/wiki/#{
      encodeURIComponent @item.name}"

    """
    <div id="buttons">

    <a class="icon-info icon-large button-icon" target="_blank"
     title="Open in Wiki" href="#{wikiLink}"></a>

    <a class="icon-shopping-cart icon-large button-icon"
     target="_blank" title="Community Market"
     href="http://steamcommunity.com/market/search?q=appid%3A440%20#{
     encodeURIComponent @item.name}"></a>

    #{@_outpostHTML()}
    #{@_wishlistHTML()}
    </div>
    """

  _buyHTML: ->
    # Buy button and store price HTML
    if @item.storePrice
      """
      <div id="buy">
      <form style="display: inline-block">$#{@item.storePrice}<br>
      <input type="text" value="1" size="1" id="quantity"
       class="textbox" style="text-align: right">
      </form><a href="#" id="buybutton"></a></div>
      """
    else ''

  _pricesLink: ->
    button = document.getElementById 'pricesource'
    prices = document.getElementById 'prices'

    if button and Object.keys(@item.prices).length > 1
      button.style.cursor = 'pointer'

      button.onclick = =>
        @_nextPriceSource()

        button.innerHTML = capitalize @source
        prices.innerHTML = @_priceSourceHTML()

      button.onmouseover = ->
        button.style.textShadow = '0 0 10px rgb(196, 241, 128)'

      button.onmouseout = ->
        button.style.textShadow = ''

  _outpostLink: ->
    # TF2Outpost link
    if window.navigator.userAgent.indexOf('Valve Steam GameOverlay') is -1
      @form.target = '_blank'

    document.getElementById('find-trades-btn').onclick = (event) =>
      tradeType = document.getElementById('tradetype').value

      @form.json.value = "{\"filters\":{},\"#{
        tradeType}\":\"440,#{@item.id},#{@form.quality.value}\"}"

      @form.submit.click()

  _wishlistLink: ->
    # Update wishlist item index
    if user.isOwnPage()
      for wish, idx in document.getElementsByClassName 'item'
        if wish.getAttribute('data-i') is @item.wishIndex
          @item.wishIndex = idx.toString()
          break

    if user.loggedIn
      action = '/wishlist/add'
      button = document.getElementById 'wishlistbutton'

      if user.isOwnPage()
        action = '/wishlist/remove'
        button.title = 'Remove from Wishlist'

      # Add to wishlist or remove from wishlist
      button.onclick = =>
        data = 'index': @item.id, 'quality': @form.quality.value

        if user.isOwnPage()
          data = 'i': @item.wishIndex

        postAjax action, data, (response) =>
          if response is 'Added'
            message = document.getElementById 'wishlistmessage'
            message.style.display = 'block'
            message.className = 'animated fadeInLeft'
            setTimeout (->
              message.className = 'animated fadeOut'), 1000

          else if response is 'Removed'
            @hide()
            @item.remove()

  _buyLink: ->
    button = document.getElementById 'buybutton'
    if button
      button.onclick = =>
        quantity = document.getElementById('quantity').value
        window.open "http://store.steampowered.com/buyitem/440/#{
          @item.id}/#{quantity}"

  _generate: ->
    # Itembox HTML
    @elem.innerHTML =
      """
      #{@_tagsHTML()}#{@_nameHTML()}#{@_classesHTML()}
      #{@_bundleHTML()}
      #{@_pricesHTML()}
      #{@_blueprintsHTML()}
      #{@_buttonsHTML()}#{@_buyHTML()}
      """

    @form = document.tf2outpostform

    @_pricesLink()
    @_outpostLink()
    @_wishlistLink()
    @_buyLink()

    # Hover area
    hoverArea = @item.elem.cloneNode true
    hoverArea.id = 'hoverarea'
    hoverArea.className = ''
    hoverArea.setAttribute 'style', "background-image: url(#{@item.imageUrl})"

    # Add hover area to itembox
    @elem.insertBefore hoverArea,
      document.getElementById('blueprints') or
      document.getElementById('buttons')

    # Enable hover box
    new HoverBox(hoverArea)

    # Auto quality selection
    # Wishlist item quality
    if @item.qualityNo
      @form.quality.value = @item.qualityNo
    else if @item.prices[@source]
      for option, i in @form.quality.options
        if option.innerHTML of @item.prices[@source]
          @form.quality.selectedIndex = i
          break

class HoverBox
  constructor: (arg) ->
    @itemBox = arg if arg instanceof ItemBox
    # Hover area
    area = arg if not @itemBox?

    @elem = document.getElementById 'hoverbox'

    if not @elem
      @elem = document.createElement 'div'
      @elem.id = 'hoverbox'
      document.getElementsByTagName('body')[0].appendChild @elem

    @_add(area)

  _add: (area) ->
    list = if area then [area] else document.getElementsByClassName 'item'

    for item in list
      item.addEventListener "mouseout", @_hide, false
      item.addEventListener "mousemove", @_moveMouse, false
      item.addEventListener "mouseover", @_show, false
      if @itemBox?
        item.addEventListener "click", @_clickItem, false

    if @itemBox?
      document.getElementsByTagName('body')[0].addEventListener "click",
                                                                @_hideItemBox,
                                                                false

      document.onkeydown = (e) => @itemBox.hide() if e.keyCode is 27

  _show: (e) =>
    item = new Item(e.target)
    description = escapeHTML item.description

    if description
      if 'bundle' in item.tags and description.indexOf('---') isnt -1
        descList = description.split '---'
        description = """
                      #{descList[0]}
                      <span style="color: #95af0c">#{descList[1]}</span>
                      """
      description = "<br>#{description}"

    @elem.innerHTML =
      """
      <div style="font-size: 1.2em; color: rgb(230, 230, 230)">#{
      item.name}</div><span style="color: gray">#{item.level}</span>#{
      item.attributes}#{description}
      """

    @elem.style.display = 'block'

  _hide: =>
    @elem.style.display = 'none'

  _hideItemBox: (e) =>
    el = e.target
    if el.className isnt 'item'
      els = []
      while el
        els.push el
        el = el.parentNode

      @itemBox.hide() if @itemBox.elem not in els

  _moveMouse: (e) =>
    @elem.style.top = "#{e.pageY + 28}px"
    @elem.style.left = "#{e.pageX - 154}px"

  _clickItem: (e) =>
    @itemBox.show e.target
    e.preventDefault()
    e.stopPropagation()

capitalize = (word) ->
  word[0].toUpperCase() + word[1...]

escapeHTML = (string) ->
  string.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

getCookie = (name) ->
  cookies = document.cookie.split ';'

  for cookie in cookies
    cookie = cookie[1...] while cookie[0] is ' '
    return cookie[name.length + 1...] if cookie[...name.length] is name

setCookie = (name, value, days) ->
  expires = ''

  if days
    date = new Date
    date.setDate(date.getDate() + days)
    expires = ";expires=#{date.toUTCString()}"

  document.cookie = "#{name}=#{value}#{expires}"

ajax = (url, callback) ->
  request = _getAjaxRequest(callback)
  request.open 'GET', url, true
  request.setRequestHeader 'X-Requested-With', 'XMLHttpRequest'
  request.send()

postAjax = (url, data, callback) ->
  request = _getAjaxRequest(callback)
  request.open 'POST', url, true
  request.setRequestHeader 'Content-Type',
                           'application/x-www-form-urlencoded'

  request.send ("#{name}=#{value}" for name, value of data).join('&')

_getAjaxRequest = (callback) ->
  request = new XMLHttpRequest

  request.onreadystatechange = ->
    if request.readyState is 4 and request.status is 200
      callback request.responseText

  return request

root.user = new User

root.ItemBox = ItemBox
root.HoverBox = HoverBox
