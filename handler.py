"""This module contains a request Handler class with template support."""
import webapp2
import jinja2
import os
import logging

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

    def handle_exception(self, exception, debug_mode):
        """Render a custom default error page"""
        if isinstance(exception, webapp2.HTTPException):
            self.response.set_status(exception.code)
        else:
            self.response.set_status(500)

        logging.exception(exception)
        self.render('error.html')
