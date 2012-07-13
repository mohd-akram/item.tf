show = (e) ->
  title = e.target.title
  description = e.target.getAttribute('data-description')
  attributes = e.target.getElementsByTagName('div')[0].innerHTML
  if description
    description = "<br>#{ description }"
  hbox.innerHTML = "<div style='font-size:1.2em;color:rgb(230,230,230)'>#{ title }</div>#{ attributes }#{ description }"
  hbox.style.display = "block"

hide = ->
  hbox.style.display = "none"

hideitembox = (e) ->
  target = e.target or e.srcElement
  if target != itembox and target not in itembox.getElementsByTagName('ul') and target not in itembox.childNodes and target.tagName not in ['LI','A','INPUT','SELECT','OPTION','H3']
    itembox.style.display='none'

moveMouse = (e) ->
  hbox.style.top = (e.pageY + 28) + "px"
  hbox.style.left = (e.pageX - 154) + "px"

window.openSummary = (e) ->
  showiteminfo(e.target)

window.showiteminfo = (element) ->
  window.itembox = document.getElementById("itembox")
  itemId = element.id
  itemName = element.title

  marketprice = element.getAttribute('data-marketprice').replace(/[{}']/g,'').replace(/, /g,'<br>')
  storeprice = element.getAttribute('data-storeprice')
  imageUrl = element.getAttribute('data-image')
  blueprints = element.getElementsByTagName('ul')

  blueprintshtml = '<div id="blueprints">'
  for b in blueprints
    chance = b.getAttribute('data-chance')

    blueprintshtml += '<ul class="blueprint">'
    for i in b.getElementsByTagName('li')
      name = i.title
      index = i.id
      style = "background-image:url(#{ i.innerHTML });"
      title = 'title="' + name + '"'
      listitem =  "<li #{ title } class='item-small' style='#{ style }'></li>"
      if index
        listitem = "<a href='/item/#{ index }' target='_blank'>" + listitem + "</a>"

      blueprintshtml = blueprintshtml + listitem
    blueprintshtml += "<li style='position:relative;top: 13px;margin-left:440px;'><h3>#{ chance }%</h3></li>"
    blueprintshtml += "</ul>"
  blueprintshtml += '</div>'

  if storeprice
    storeprice = "$#{ storeprice }"
    buyButton = "<form style='position:absolute;bottom:19px;left:345px;'>#{ storeprice }<br><input type='text' value='1' size='1' id='quantity' class='textbox'></form><a href='#' id='buy-button'></a>"
  else
    buyButton = ''

  wikilink = 'href="http://wiki.teamfortress.com/wiki/' + itemName + '"'

  itembox.innerHTML = "<h2>#{ itemName }</h2>
    <a class='button' target='_blank' title='Open in Wiki' style='position:absolute;bottom:10px;left:10px;' #{ wikilink }>Wiki</a>
    <h3>#{ marketprice }</h3>
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
    #{ blueprintshtml }"

  itembox.style.display = "block"
  itembox.style.backgroundImage = "url('#{ imageUrl }')"

  buy = document.getElementById('buy-button')
  if buy
    buy.onclick = ->
      quantity = document.getElementById('quantity').value
      window.open("http://store.steampowered.com/buyitem/440/#{ itemId }/#{ quantity }")

  quality = document.tf2outpostform.quality
  quality.onchange = ->
    document.tf2outpostform.has1.value = "440,#{ itemId },#{ quality.value }"

window.onload = ->
  window.hbox = document.getElementById("hoverbox")

  if hbox
    icells = document.getElementsByTagName("li")
    for cell in icells
      cell.addEventListener("mouseout", hide, false)
      cell.addEventListener("mousemove", moveMouse, false)
      cell.addEventListener("mouseover", show, false)
      cell.addEventListener("click", openSummary, false)

    document.addEventListener("click",hideitembox, false)
