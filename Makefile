install:
	# 1. Install packages
	pkg install -y nginx python3 redis
	mkdir -p /usr/local/etc/rc.conf.d
	echo 'nginx_enable="YES"' > /usr/local/etc/rc.conf.d/nginx
	echo 'redis_enable="YES"' > /usr/local/etc/rc.conf.d/redis
	# 2. Create user
	pw user add item.tf -c item.tf -d /nonexistent -s /usr/sbin/nologin
	# 3. Create log folder
	mkdir -p /var/log/item.tf
	chown item.tf:item.tf /var/log/item.tf
	# 4. Setup virtualenv
	python3 -m venv /usr/local/libexec/item.tf
	. /usr/local/libexec/item.tf/bin/activate && \
	cd /usr/local/www/item.tf && \
	pip install --upgrade pip && \
	pip install -r requirements.txt && \
	pip install gunicorn
	# 5. Link configs
	ln -s -f /usr/local/www/item.tf/etc/nginx/nginx.conf \
		/usr/local/etc/nginx/nginx.conf
	ln -s -f /usr/local/www/item.tf/etc/rc.d/itemtf \
		/usr/local/etc/rc.d/itemtf
	ln -s -f /usr/local/www/item.tf/var/cron/tabs/item.tf \
		/var/cron/tabs/item.tf
	# 6. Start server
	service redis restart
	service itemtf restart
	[ -e /usr/local/etc/ssl/dhparam.pem ] || \
		openssl dhparam -out /usr/local/etc/ssl/dhparam.pem 2048
	service nginx restart

uninstall:
	-service itemtf stop
	-rm -rf /usr/local/libexec/item.tf
	-rm -rf /var/log/item.tf
	-rm /usr/local/etc/rc.d/itemtf
	-rm /var/cron/tabs/item.tf
	-pw user del item.tf
