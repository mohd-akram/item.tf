"""This module contains a request Handler class with template support."""
import webapp2
import jinja2
import os

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),
                               autoescape=True, trim_blocks=True)

class Handler(webapp2.RequestHandler):
    """A request handler with template support"""
    def write(self, *args, **kwargs):
        """Write text to HTTP response body"""
        self.response.out.write(*args, **kwargs)

    def _render_str(self, template, **params):
        """Render HTML template"""
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kwargs):
        """Render HTML template and write it to HTTP response body"""
        self.write(self._render_str(template, **kwargs))