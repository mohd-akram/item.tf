install:
	# 1. Create user
	-pw user add itemtf -c item.tf -d /nonexistent -s /usr/sbin/nologin
	# 2. Setup virtualenv
	python3.14 -m venv /usr/local/libexec/item.tf
	. /usr/local/libexec/item.tf/bin/activate && \
	pip install --upgrade -r requirements.txt pip
	# 3. Link configs
	mkdir -p /usr/local/etc/nginx/conf.d
	ln -s -f $(.CURDIR)/etc/nginx/conf.d/item.tf.conf \
		/usr/local/etc/nginx/conf.d/item.tf.conf
	ln -s -f $(.CURDIR)/etc/rc.d/itemtf \
		/usr/local/etc/rc.d/itemtf
	ln -s -f $(.CURDIR)/var/cron/tabs/itemtf \
		/var/cron/tabs/itemtf
	# 4. Start server
	service itemtf restart
	service nginx reload

uninstall:
	-service itemtf stop
	-rm -rf /usr/local/libexec/item.tf
	-rm /usr/local/etc/nginx/conf.d/item.tf.conf
	-rm /usr/local/etc/rc.d/itemtf
	-rm /var/cron/tabs/itemtf
	-pw user del itemtf

upgrade:
	. /usr/local/libexec/item.tf/bin/activate && \
	pip install --upgrade-strategy eager --upgrade -r requirements.txt pip
