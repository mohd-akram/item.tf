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
import logging

import handler

from tf2 import TF2Handler, TF2ResultsHandler, TF2ItemHandler

app = webapp2.WSGIApplication([('/', TF2Handler),
                               ('/search', TF2ResultsHandler),
                               ('/item/([0-9]+)(.json)?', TF2ItemHandler)],
                              debug=True)