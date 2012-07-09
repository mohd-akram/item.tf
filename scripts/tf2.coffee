show = (e) ->
  hbox.innerHTML = e.target.title
  hbox.style.display = "block"

hide = ->
  hbox.style.display = "none"

hideitembox = (e) ->
  target = e.target or e.srcElement
  if target != itembox and target not in itembox.getElementsByTagName('ul') and target not in itembox.childNodes and target.tagName not in ['LI','A','INPUT','SELECT','OPTION']
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

  blueprintshtml = '<div id="blueprint">'
  for b in blueprints
    chance = b.getAttribute('data-chance')

    blueprintshtml += '<ul style="width:auto;margin:0">'
    for i in b.getElementsByTagName('li')
      name = i.title
      index = i.id
      style = "background-image:url(#{ i.innerHTML });"
      listitem =  "<li title='#{ name }' class='item-small' style='#{ style }'></li>"
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

  itembox.innerHTML = "<h2>#{ itemName }</h2>
    <a class='button' target='_blank' style='position:absolute;bottom:10px;left:10px;' href='http://wiki.teamfortress.com/wiki/#{ itemName }'>Open in Wiki</a>
    <h3>#{ marketprice }</h3>
    <form name='tf2outpostform' method='POST' action='http://www.tf2outpost.com/search' target='_blank'>
      <input type='hidden' name='has1' value='440,#{ itemId },6'>
      <input class='button' style='position:absolute;bottom:10px;left:138px;margin:0;' type='submit' name='submit' value='Find trades'>
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
