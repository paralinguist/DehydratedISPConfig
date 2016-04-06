# LetsEncryptISPConfig
Provides LE to ISPConfig hosted sites, including master/slave

## Requirements:
1. letsencrypt.sh: git clone https://github.com/lukas2511/letsencrypt.sh  
2. oursql: pip install oursql  
3. tld:    pip install tld  

### config.sh
Create a config.sh file in the letsencrypt.sh directory with the following contents:  
__IMPORTANT__ Make sure you set the email correctly.
```bash
####WARNING#####
#If you change between authorities (eg, testing to live) you MUST delete
#private_key.pem in your BASEDIR
CA="https://acme-v01.api.letsencrypt.org/directory"
#CA="https://acme-staging.api.letsencrypt.org/directory"
BASEDIR="/etc/ssl/private"
WELLKNOWN="/var/le-ispconfig/"
# E-mail to use during the registration (default: <unset>)
CONTACT_EMAIL="you@example.com"
```

### Create the wellknown:
`mkdir /var/le-ispconfig`  

### Apache Config
Create `letsencrypt.conf` in the apache conf folders (usually `/etc/apache2/conf-available/`):
```apacheconf
Alias "/.well-known/acme-challenge/" /var/le-ispconfig/  
<Directory /var/le-ispconfig>  
  Require all granted  
</Directory>  

<IfModule mod_headers.c>  
  <LocationMatch "/.well-known/acme-challenge/*">  
    Header set Content-Type "text/plain"  
  </LocationMatch>  
</IfModule>
```  
Enable the config:  
`a2enconf letsencrypt`  
Restart Apache:  
`service apache2 restart`