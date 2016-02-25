# LetsEncryptISPConfig
Provides LE to ISPConfig hosted sites, including master/slave

Requirements:
letsencrypt.sh: git clone https://github.com/lukas2511/letsencrypt.sh
oursql: pip install oursql
tld:    pip install tld

###config.sh###
change basedir to /etc/ssl/private
change wellknown to /var/le-ispconfig/
change contact email

#Create the wellknown:
mkdir /var/le-ispconfig

#letsencrypt.conf in the apache conf folders:

Alias "/.well-known/acme-challenge/" /var/le-ispconfig/
<Directory /var/le-ispconfig>
  Require all granted
</Directory>
<IfModule mod_headers.c>
  <LocationMatch "/.well-known/acme-challenge/*">
    Header set Content-Type "text/plain"
  </LocationMatch>
</IfModule>

 Currently: If the site has no SSL enabled, you need to tick it in ISPConfig and then save an empty cert on the SSL tab 
 (add a BEGIN and END with no content to the cert, change dropdown to save and click. This is stupid.)
