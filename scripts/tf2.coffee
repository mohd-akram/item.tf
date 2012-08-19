show = (e) ->
  title = e.target.title

  attributes = getattributes(e.target)
  description = getdescription(e.target)
  description = if description then '<br>'+description else description

  hbox.innerHTML = "<div style='font-size:1.2em;color:rgb(230,230,230)'>#{ title }</div>#{ attributes }#{ description }"
  hbox.style.display = "block"

getattributes = (item) ->
  divs = item.getElementsByTagName('div')
  attributes = if divs.length>0 then divs[0].innerHTML else ''
  return attributes

getdescription = (item) ->
  description = item.getAttribute('data-description')
  description ?= ''
  return description

capitalize = (word) ->
  return word[0].toUpperCase() + word[1...]

hide = ->
  hbox.style.display = "none"

window.hideitembox = (e) ->
  target = e.target or e.srcElement
  if target != itembox and target not in itembox.getElementsByTagName('ul') and target not in itembox.childNodes and target.tagName not in ['LI','A','INPUT','SELECT','OPTION','H3','IMG']
    itembox.style.display='none'

moveMouse = (e) ->
  hbox.style.top = (e.pageY + 28) + "px"
  hbox.style.left = (e.pageX - 154) + "px"

window.openSummary = (e) ->
  showiteminfo(e.target)

window.showiteminfo = (element) ->
  window.hbox = document.getElementById('hoverbox')
  window.itembox = document.getElementById("itembox")
  itemId = element.id
  itemName = element.title

  # Market price HTML
  marketprice = element.getAttribute('data-marketprice')
  if marketprice
    for i in ['Unique','Vintage','Strange','Genuine','Haunted']
      re = new RegExp(i,"g")
      marketprice = marketprice.replace(/[{}']/g,'').replace(/, /g,'<br>').replace(re,"<span class='#{ i.toLowerCase() }'>#{ i }</span>")
    marketprice = '<h3 id="marketprice">'+marketprice+'</h3>'
  else
    marketprice = ''

  storeprice = element.getAttribute('data-storeprice')
  imageUrl = element.getAttribute('data-image')
  blueprints = element.getElementsByTagName('ul')

  # Blueprints HTML
  blueprintshtml = '<div id="blueprints">'
  for b in blueprints
    chance = b.getAttribute('data-chance')

    blueprintshtml += '<ul class="blueprint">'
    for i in b.getElementsByTagName('li')
      for j in [0...i.getAttribute('data-count')]
        name = i.title
        index = i.id
        style = "background-image:url(#{ i.getAttribute('data-image') });"
        title = 'title="' + name + '"'
        listitem =  "<li #{ title } class='item-small' style='#{ style }'></li>"
        if index
          listitem = "<a href='/item/#{ index }' target='_blank'>" + listitem + "</a>"

        blueprintshtml += listitem
    blueprintshtml += "<li title='Crafting Chance' style='position:relative;top: 13px;margin-left:440px;'><h3>#{ chance }%</h3></li>"
    blueprintshtml += "</ul>"
  blueprintshtml += '</div>'

  # Buy button and price HTML
  if storeprice
    storeprice = "$#{ storeprice }"
    buyButton = "<form style='position:absolute;bottom:19px;left:345px;'>#{ storeprice }<br><input type='text' value='1' size='1' id='quantity' class='textbox'></form><a href='#' id='buy-button'></a>"
  else
    buyButton = ''

  wikilink = 'href="http://wiki.teamfortress.com/wiki/' + itemName + '"'

  # Classes HTML
  classeshtml = "<div id='classes' style='position:absolute;top:0;right:0'>"
  classes = element.getAttribute('data-classes')
  if classes
    for i in classes.split(',')
      classeshtml += "<a href='/search?q=#{ i }' target='_blank'><img title='#{ i }' width='40px' height='40px' src='/images/items/#{ i }_icon.png'></a><br>"
  classeshtml += "</div>"

  # Tags HTML
  tagshtml = "<div id='tags' style='position:absolute;top:-5px;left:5px'>"
  tags = element.getAttribute('data-tags')
  if tags
    tags = tags.split(',')
    isweapon = 'weapon' in tags
    istoken = 'token' in tags

    title = image = ''
    for i in ['primary','secondary','melee','pda2']
      if i in tags
        if isweapon
          title =  capitalize(i)+' Weapon'
          image = i

        else if istoken
          title = 'Slot Token'
          image = 'slot_token'

    for i in ['hat','misc']
      if i in tags
        title = capitalize(i)
        image = i

    if istoken and classes != null
      title = 'Class Token'
      image = 'class_token'

    if title and image
      tagshtml += "<a href='/search?q=#{ title }' target='_blank'><img title='#{ title }' width='50px' height='50px' src='/images/items/#{ image }.png'></a><br>"
  tagshtml += "</div>"
      
  # Itembox HTML
  itembox.innerHTML = "<h2 id='itemname'><a href='/item/#{itemId}' target='_blank' title='Go to Item Page'>#{ itemName }</a></h2>
    <a class='button' target='_blank' title='Open in Wiki' style='position:absolute;bottom:10px;left:10px;' #{ wikilink }>Wiki</a>
    #{ marketprice }
    <form name='tf2outpostform' method='POST' action='http://www.tf2outpost.com/search' target='_blank'>
      <input type='hidden' name='has1' value='440,#{ itemId },6'>
      <input class='button' style='position:absolute;bottom:10px;left:70px;margin:0;' type='submit' title='Find trades' name='submit' value='Trades'>
      <input type='hidden' name='type' value='any'>
      <select id='quality' class='textbox' style='text-align:left'>
        <option value='6' selected=''>Unique</option>
        <option value='3'>Vintage</option>
        <option value='1'>Genuine</option>
        <option value='5'>Unusual</option>
        <option value='11'>Strange</option>
        <option value='13'>Haunted</option>
      </select>
    </form>
    #{ buyButton }
    #{ blueprintshtml }
    #{ classeshtml }
    #{ tagshtml }"

  itembox.style.display = "block"
 
  # Hover area
  hoverarea = document.createElement('div')
  hoverarea.title = element.title
  hoverarea.setAttribute('data-description',getdescription(element))
  hoverarea.id = 'hoverarea'
  hoverarea.style.backgroundImage = "url('#{ imageUrl }')"
  hoverarea.innerHTML = '<div style="display:none">'+getattributes(element)+'</div>'
  hoverarea.addEventListener("mouseout", hide, false)
  hoverarea.addEventListener("mousemove", moveMouse, false)
  hoverarea.addEventListener("mouseover", show, false)
  itembox.appendChild(hoverarea)

  # Buy button link
  buy = document.getElementById('buy-button')
  if buy
    buy.onclick = ->
      quantity = document.getElementById('quantity').value
      window.open("http://store.steampowered.com/buyitem/440/#{ itemId }/#{ quantity }")

  # TF2Outpost link
  quality = document.tf2outpostform.quality
  quality.onchange = ->
    document.tf2outpostform.has1.value = "440,#{ itemId },#{ quality.value }"

window.onload = ->
  window.hbox = document.getElementById("hoverbox")

  if hbox
    for i in document.getElementsByClassName('itemlist')
      for cell in i.getElementsByTagName('li')
        cell.addEventListener("mouseout", hide, false)
        cell.addEventListener("mousemove", moveMouse, false)
        cell.addEventListener("mouseover", show, false)
        cell.addEventListener("click", openSummary, false)
