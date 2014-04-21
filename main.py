#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
from webapp2_extras.routes import DomainRoute

from tf2 import (TF2Handler, TF2SearchHandler, TF2SuggestHandler,
                 TF2UserHandler, TF2WishlistHandler, TF2ItemHandler,
                 TF2SitemapHandler, CacheHandler, RedirectHandler)


app = webapp2.WSGIApplication([DomainRoute(r'<:(www\..+|.+\.appspot\.com)>',
                               [webapp2.Route(r'/<:.*>', RedirectHandler)]),
                               (r'/', TF2Handler),
                               (r'/search(\.json)?', TF2SearchHandler),
                               (r'/suggest', TF2SuggestHandler),
                               (r'/(profiles)/([0-9]+)', TF2UserHandler),
                               (r'/(id)/([A-Za-z0-9_-]+)', TF2UserHandler),
                               (r'/wishlist/(add|remove)', TF2WishlistHandler),
                               (r'/([0-9]+)(\.json)?', TF2ItemHandler),
                               (r'/item/([0-9]+)(\.json)?', TF2ItemHandler),
                               (r'/sitemap\.xml', TF2SitemapHandler)])

cache = webapp2.WSGIApplication([(r'/cache/(update|flush)', CacheHandler)])
