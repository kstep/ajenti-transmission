# Transmission control plugin for Ajenti

This is an [Ajenti][] plugin to control [Transmission][] torrent client.
It also requires [models][] Ajenti plugin.

Install **models** plugin into `/var/lib/ajenti/plugins` along with this plugin and restart **Ajenti**:

```
# mkdir -p /var/lib/ajenti/plugins/{models,transmission}
# git clone https://github.com/kstep/ajenti-models.git /var/lib/ajenti/plugins/models
# git clone https://github.com/kstep/ajenti-transmission.git /var/lib/ajenti/plugins/transmission
# service restart ajenti
```

You will also need to compile `content/js/dom.coffee` file with [CoffeeScript][] compiler:

```
# cd /var/lib/ajenti/plugins/transmission/content/js
# coffee -c dom.coffee && mv dom.js dom.coffee.js && cp dom.coffee.js dom.coffee.c.js
```

Now login to your Ajenti panel and go to new **Transmission** menu item in **Software** section. You may need to configure it.

[Ajenti]: http://ajenti.org/
[Transmission]: http://www.transmissionbt.com/
[models]: http://github.com/kstep/ajenti-models
[CoffeeScript]: http://coffeescript.org/
