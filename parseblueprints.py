from urllib2 import urlopen
import re

data = urlopen('http://www.tf2crafting.info/blueprints/').read()
matches = re.findall(r'<td style="vertical\-align: top; padding-top: 18px;"><b>Fabricate ([^<]+)<\/b><\/td>(.+)',data,flags=re.DOTALL)
print(matches)