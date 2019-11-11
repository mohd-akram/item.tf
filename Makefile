install:
	# 1. Create user
	-pw user add item.tf -c item.tf -d /nonexistent -s /usr/sbin/nologin
	# 2. Setup virtualenv
	python3.8 -m venv /usr/local/libexec/item.tf
	. /usr/local/libexec/item.tf/bin/activate && \
	pip install --upgrade pip && \
	pip install -r requirements.txt
	# 3. Link configs
	mkdir -p /usr/local/etc/nginx/conf.d
	ln -s -f $(.CURDIR)/etc/nginx/conf.d/item.tf.conf \
		/usr/local/etc/nginx/conf.d/item.tf.conf
	ln -s -f $(.CURDIR)/etc/rc.d/itemtf \
		/usr/local/etc/rc.d/itemtf
	ln -s -f $(.CURDIR)/var/cron/tabs/item.tf \
		/var/cron/tabs/item.tf
	# 4. Start server
	service itemtf restart
	service nginx reload

uninstall:
	-service itemtf stop
	-rm -rf /usr/local/libexec/item.tf
	-rm /usr/local/etc/nginx/conf.d/item.tf.conf
	-rm /usr/local/etc/rc.d/itemtf
	-rm /var/cron/tabs/item.tf
	-pw user del item.tf
