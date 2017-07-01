server {
  listen [::]:80;
  server_name item.tf www.item.tf;
  include common;
  location / {
    return 301 https://item.tf$request_uri;
  }
}

server {
  listen [::]:443 ssl;
  server_name www.item.tf;
  include common;
  location / {
    return 301 https://item.tf$request_uri;
  }
}

server {
  listen [::]:443 ssl http2;

  server_name item.tf;

  include common;

  root /usr/local/www/item.tf/static;

  location ~* \.(js|css|png|jpg|jpeg|gif|ico)$ {
    try_files $uri @app;
    expires 1w;
  }

  location / {
    try_files $uri @app;
  }

  location @app {
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header Host $http_host;
    proxy_redirect off;
    proxy_pass http://localhost:8000;
  }
}
