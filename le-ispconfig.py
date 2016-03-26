#!/usr/bin/python
#TODO: Push SSL cert contents back into ISPConfig DB
import os
import oursql
from collections import defaultdict
from tld import get_tld
from tld.utils import update_tld_names
import subprocess

#Change these settings to suit your configuration
CERT_LOCATION = "/etc/ssl/private/certs/"
DOMAINS_TXT = "/etc/ssl/private/domains.txt"
ISP_CONFIG = "/usr/local/ispconfig/"
ISP_CONFIG_CONFIG = ISP_CONFIG + "server/lib/config.inc.php"
ISP_CONFIG_SSL = ISP_CONFIG + "interface/ssl/"
LE_SH_LOCATION = "./"
#Your system's HTTPD restart command as an array of command and any args
RESTART_HTTPD = ("/usr/sbin/service", "apache2", "restart")
#(optional) the domain you access ISPConfig's CP with
#If set, will update the cert for the ISPCOnfig app
PANEL_DOMAIN = "ihle.in"

update_tld_names()

host = ""
database = ""
user = ""
password = ""

restartNeeded = False

#Parse the ISPConfig settings for DB details
for line in open(ISP_CONFIG_CONFIG):
  if "$conf['db_host']" in line:
    host = line.split(" = ")[-1].split("'")[1]
  elif "$conf['db_database']" in line:
    database = line.split(" = ")[-1].split("'")[1]
  elif "$conf['db_user']" in line:
    user = line.split(" = ")[-1].split("'")[1]
  elif "$conf['db_password']" in line:
    password = line.split(" = ")[-1].split("'")[1]
  if (host and database and user and password):
    break;

ispconfigDB = oursql.connect(host, user, password, db=database)

#Grab active domain details
with ispconfigDB.cursor() as domainQuery:
  domainQuery.execute("""
    SELECT s.domain, s.subdomain, s.document_root, d.domain AS parent
    FROM web_domain s
    LEFT JOIN web_domain d ON s.parent_domain_id = d.domain_id
    WHERE s.active = 'y'
    ORDER BY parent
    """)
  domains = defaultdict(dict)
  #The following logic is based on the assumption that non-alias domains are
  #encountered first. Probably safe, but potentially iffy.
  for row in domainQuery:
    domain = row[0]
    subdomain = row[1]
    path = row[2]
    alias = row[3]
    if alias:
      parentDomain = alias
      path = ""
      print domain + " is an alias for " + alias
    else:
      parentDomain = get_tld("http://" + domain)
      print domain + " is a vhost for " + parentDomain
    if os.path.isdir(path) or alias in domains:
      print domain + " is hosted here..."
      domains[parentDomain][domain] = {}
      domains[parentDomain][domain]["site"] = domain
      domains[parentDomain][domain]["path"] = path
      if subdomain == "www":
        print "(added www subdomain for " + domain + ")"
        domains[parentDomain]["www." + domain] = {}
        domains[parentDomain]["www." + domain]["site"] = "www." + domain
        domains[parentDomain]["www." + domain]["path"] = ""

#Dump the sites hosted here into the domains config file
certificateLocations = {}
with open(DOMAINS_TXT, "w") as domainList:
  for parent, sites in domains.iteritems():
    for site in sites:
      print >> domainList, site,
      if parent not in certificateLocations:
        certificateLocations[parent] = site
    print >> domainList

#Call the LE shellscript
certResult = subprocess.Popen([LE_SH_LOCATION + "letsencrypt.sh", "--cron"], stdout=subprocess.PIPE)

#Parse the output of LE to find evidence of updated certs
for line in certResult.stdout:
  print line
  if " + Done!" in line:
    restartNeeded = True
    break

if restartNeeded:
  print "Changes made - updating config and restarting HTTPD"
  for parent, sites in domains.iteritems():
    #try n except here plox
    print "Attempting to read "+parent+"(" + certificateLocations[parent] + ")" + " cert and key..."
    with open(CERT_LOCATION + certificateLocations[parent] + "/fullchain.pem", "r") as certFile:
      certificate = certFile.read()
    with open(CERT_LOCATION + certificateLocations[parent] + "/privkey.pem", "r") as keyFile:
      key = keyFile.read()

    with ispconfigDB.cursor() as updateQuery:
      print "Attempting to update ISPConfig..."
      updateSQL = """
        UPDATE web_domain
        SET `ssl`='y', ssl_cert=?, ssl_key=?, ssl_request='', ssl_bundle=''
        WHERE domain IN (?)"""
      updateQuery.execute(updateSQL, (certificate, key, "','".join(sites)))
    #TODO: exception handling for symlinking
    for site, details in sites.iteritems():
      if details["path"] != "":
        #TODO: take note of first domain in list - since LE clients
        #are completely stubborn about not letting you set cert locations
        certificateFile = CERT_LOCATION+certificateLocations[parent]+"/fullchain.pem"
        certificateTarget = details["path"] + "/ssl/" + site + ".crt"
        keyFile = CERT_LOCATION +certificateLocations[parent]+ "/privkey.pem"
        keyTarget = details["path"] + "/ssl/" + site + ".key"
        print "Linking: " + certificateFile + " to: " + certificateTarget
      
        try:
          os.remove(certificateTarget)
        except:
          pass
        os.symlink(certificateFile, certificateTarget)
        try:
          os.remove(keyTarget)
        except:
          pass
        os.symlink(keyFile, keyTarget)
        if site == PANEL_DOMAIN:
          try:
            os.remove(ISP_CONFIG_SSL + "ispserver.crt")
          except:
            pass
          os.symlink(certificateFile, ISP_CONFIG_SSL + "ispserver.crt")
          try:
            os.remove(ISP_CONFIG_SSL + "ispserver.key")
          except:
            pass
          os.symlink(keyFile, ISP_CONFIG_SSL + "ispserver.key")
   
      #check user settings to force SSL redirect via apache_directives
  
  subprocess.call(RESTART_HTTPD)
else:
  print "No changes made"
