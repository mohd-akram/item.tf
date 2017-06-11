install:
	# 1. Create user
	-pw user add item.tf -c item.tf -d /nonexistent -s /usr/sbin/nologin
	# 2. Create log folder
	mkdir -p /var/log/item.tf
	chown item.tf:item.tf /var/log/item.tf
	# 3. Setup virtualenv
	python3 -m venv /usr/local/libexec/item.tf
	. /usr/local/libexec/item.tf/bin/activate && \
	cd /usr/local/www/item.tf && \
	pip install --upgrade pip && \
	pip install -r requirements.txt && \
	pip install gunicorn
	# 4. Link configs
	mkdir -p /usr/local/etc/nginx/conf.d
	ln -s -f /usr/local/www/item.tf/etc/nginx/conf.d/item.tf.conf \
		/usr/local/etc/nginx/conf.d/item.tf.conf
	ln -s -f /usr/local/www/item.tf/etc/rc.d/itemtf \
		/usr/local/etc/rc.d/itemtf
	ln -s -f /usr/local/www/item.tf/var/cron/tabs/item.tf \
		/var/cron/tabs/item.tf
	# 5. Start server
	service itemtf restart
	service nginx reload

uninstall:
	-service itemtf stop
	-rm -rf /usr/local/libexec/item.tf
	-rm -rf /var/log/item.tf
	-rm /usr/local/etc/rc.d/itemtf
	-rm /var/cron/tabs/item.tf
	-pw user del item.tf
