# Author: AAnkers
# Date: 26-Sep-2022
# Description: Convert Microsoft Azure JSON Feed into Junos SRX Firewall Rules
from netmiko import ConnectHandler
import json
import requests
import os
import re
import datetime

# Define constants
AZURE_JSON_URL = 'https://www.microsoft.com/en-us/download/confirmation.aspx?id=56519' # Microsoft Azure IP Range JSON URL
CUSTOM_AZURE_CUSTOM_IPS = ['52.239.158.0/23', '20.60.178.0/23', '52.239.248.0/24', '52.239.140.0/22', '20.47.7.0/24', '20.47.18.0/23', '20.47.30.0/24', '20.60.26.0/23', '20.60.130.0/24', '20.60.150.0/23', '20.60.196.0/23', '20.150.8.0/23', '20.150.37.0/24', '20.150.42.0/24', '20.150.74.0/24', '20.150.76.0/24', '20.150.83.0/24', '20.150.122.0/24', '20.157.33.0/24', '52.239.212.0/23', '52.239.242.0/23', '20.38.102.0/23', '20.47.8.0/24', '20.47.20.0/23', '20.47.32.0/24', '20.60.19.0/24', '20.60.40.0/23', '20.60.144.0/23', '20.60.204.0/23', '20.150.26.0/24', '20.150.47.128/25', '20.150.48.0/24', '20.150.75.0/24', '20.150.84.0/24', '20.150.104.0/24', '52.239.136.0/22', '20.60.166.0/23', '51.141.129.64/26', '52.239.231.0/24', '52.246.251.248/32', '20.47.34.0/24', '20.47.56.0/24', '20.60.17.0/24', '20.60.164.0/23', '20.150.46.0/24', '20.150.69.0/24', '20.150.110.0/24', '20.157.46.0/24', '20.157.157.0/24', '20.209.6.0/23', '20.60.222.0/23'] # Azure Public IPs not in the JSON File but which need to be allowed-through
OUTPUT_JSON_FILE = '/opt/scripts/azure-json-ip-srx-checker/Azure_IPs.json' # Downloaded Microsoft Azure IP Addresses JSON file
OUTPUT_SRX_CURRENT = '/opt/scripts/azure-json-ip-srx-checker/srx_config_current.txt' # Current Juniper Config
OUTPUT_DELTA_CONFIG = '/opt/scripts/azure-json-ip-srx-checker/azure_srx_delta_config.txt' # Delta between Processed Azure SRX Config and Current SRX Config
AZURE_SRX_MAP = {'Sql':'AZURE_SQL_GLOBAL', 'Storage':'AZURE_STORAGE_GLOBAL', 'AzureCosmosDB':'AZURE_COSMOSDB_GLOBAL'} # Azure Service name (as used in Microsoft JSON) to SRX Address Set name
AZURE_IP_VERSION = "IPv4" # IP Address Versions to match, "IPv4" for just IPv4 or "IPv6" for both
HTTP_PROXY = {"https": "http://proxyuser:proxypassword@proxy.yourcompany.com:8080"} # Company Web Proxy settings (assumed Port 8080 but could be others)
SSH_IP = '10.99.99.99' # SRX Network Device Management IP Address
SSH_USER = 'admin' # SRX Network Device RO User
SSH_PASS = 'Password1234' # SRX Network Device RO Pass

# Functions
# Find the index of an element in a list
def listIndexFind(lst, key, value):
 for i, dic in enumerate(lst):
  if dic[key] == value:
   return i
 return -1


# Main program
# Initialise variables
file_output = ''
print("JOB START: " + datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z") + "\n")

# Download current JSON (Microsoft do a JavaScript redirect, so need to rip out the JSON file from the HTTP response)
print("Downloading latest Microsoft Azure JSON File [" + AZURE_JSON_URL +"]...")
json_html = requests.get(AZURE_JSON_URL, proxies=HTTP_PROXY)
# Find the actual .json file URL embedded in the Microsoft download HTML page
json_url = re.findall('(https://.*json)', json_html.content.decode('UTF-8'))
r = requests.get(json_url[1], proxies=HTTP_PROXY)
# Output status based on HTTP Status Code
if r.status_code == 200:
 print(" Success [HTTP " + str(r.status_code) + "]")
else:
 print(" Error [HTTP " + str(r.status_code) + "]")
# Save as the relevant filename.json
with open(OUTPUT_JSON_FILE, 'wb') as f:
 f.write(r.content)

# Output to log
print('\nGrabbing Azure-specific configuration from current SRX Firewall...')
# Use Netmiko to establish a SSH connection to the SRX Firewall
netmiko_connection = {
 'device_type': 'juniper',
 'ip': SSH_IP,
 'username': SSH_USER,
 'password': SSH_PASS,
 'port' : 22,
 'verbose': True
}
ssh_connection = ConnectHandler(**netmiko_connection)
ssh_connection.ansi_escape_codes = True
# Junos CLI Command to scrape Azure-specific Firewall Configuration
cli_command = 'show configuration | display set | match "AZURE_" | no-more'
print(' ' + cli_command)
# Execute command against Firewall
result = ssh_connection.send_command(cli_command, delay_factor=2)
# Close SSH Connection
ssh_connection.disconnect()
# Write to Current SRX Config file
with open(OUTPUT_SRX_CURRENT, 'w') as srx_current_out:
 srx_current_out.write(result)

# Load latest Azure JSON file in
with open(OUTPUT_JSON_FILE) as f:
 json_curr_parsed = json.load(f)

# Load current SRX Config file in
srx_azure_file = open(OUTPUT_SRX_CURRENT, 'r')
srx_azure_list = srx_azure_file.readlines()
srx_azure_file.close()

# List Azure Services available vs those being checked
print("\nProcessing enabled [*] for the following available Azure Services (as per: " + AZURE_JSON_URL + ")...")
for available_azure_service in json_curr_parsed.get('values'):
 # Only list non-regional Azure Global Services (i.e. without Service.Region format)
 if available_azure_service.get('name').find('.') == -1:
  # Affix asterisk if Service is selected
  if available_azure_service.get('name') in AZURE_SRX_MAP:
   print(" [*" + available_azure_service.get('name') + "]")
  else:
   print(" " + available_azure_service.get('name'))
   
# Loop through each Azure Service to SRXify
for azure_service in AZURE_SRX_MAP:
 print("\nProcessing Azure Service [" + azure_service + "]")
 # Check new JSON against existing SRX Firewall Rules (adds)
 print(" Checking Microsoft JSON entries against current Firewall Rules...")
 
 # Find index of azure_service in current Microsoft JSON
 json_curr_index = listIndexFind(json_curr_parsed.get('values'), 'name', azure_service)
 # Loop through each Azure Service IPs in Microsoft JSON
 for ip_address_curr in json_curr_parsed.get('values')[json_curr_index].get('properties').get('addressPrefixes'):
  # Only process IPv4 or both IPv4 and IPv6 addresses
  if (((AZURE_IP_VERSION == "IPv4") and (re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", ip_address_curr) != None)) or (AZURE_IP_VERSION == "IPv6")):
   # Check if current Azure Service IP Address in current SRX Firewall config, unchanged
   if ip_address_curr in str(srx_azure_list):
    # IP Address present in both, no action needed, output to log
    print("  [" + azure_service + ", NoChange] " + ip_address_curr)
   else:
    # IP Address not present in current SRX Firewall config, addition needed
    print("  [" + azure_service + ", Add] " + ip_address_curr)
    # Generate SRX Address List syntax
    file_output += "set security zones security-zone ExpressRoute-Public address-book address AZURE_PAAS_" + ip_address_curr + " " + ip_address_curr + "\n"
    # Generate SRX Address Set syntax
    file_output += "set security zones security-zone ExpressRoute-Public address-book address-set " + AZURE_SRX_MAP[azure_service] + " address AZURE_PAAS_" + ip_address_curr + "\n!\n" 

 # Output to log
 print("\n Checking current Firewall Rules against Microsoft JSON entries...")
 # Loop through each Azure Service in SRX Firewall
 for azure_firewallline in srx_azure_list:
  # Only process lines that match Address Sets for current Azure Service being processed
  if ("set security zones security-zone ExpressRoute-Public address-book address-set " + AZURE_SRX_MAP[azure_service]) in azure_firewallline:
   # Extract IP Address from current SRX config line
   ip_firewallline = re.findall(r'([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\/[0-9]{2})', azure_firewallline)
   # Ignore deletes for custom Azure IPs (not in Microsoft JSON file but which need to be allowed-through)
   if ip_firewallline[0] in CUSTOM_AZURE_CUSTOM_IPS:
    # Custom IP present, no action needed, output IP Address
    print("  [" + azure_service + ", NoChange_Custom] " + ip_firewallline[0])
   else:
    # Check if current Firewall Line IP Address in Microsoft JSON file
    if ip_firewallline[0] in open(OUTPUT_JSON_FILE).read():
     # IP Address present in both, no action needed, output IP Address
     print("  [" + azure_service + ", NoChange] " + ip_firewallline[0])
    else:
     # IP Address missing from Microsoft JSON file, delete
     print("  [" + azure_service + ", Delete] " + ip_firewallline[0])

     # Generate SRX Address List syntax
     file_output += "delete security zones security-zone ExpressRoute-Public address-book address AZURE_PAAS_" + ip_firewallline[0] + " " + ip_firewallline[0] + "\n"
     # Generate SRX Address Set syntax
     file_output += "delete security zones security-zone ExpressRoute-Public address-book address-set " + AZURE_SRX_MAP[azure_service] + " address AZURE_PAAS_" + ip_firewallline[0] + "\n!\n" 

# Ouput delta SRX syntax
print("\nWriting delta Junos SRX syntax to file [" + OUTPUT_DELTA_CONFIG + "]...")
try:
 f = open(OUTPUT_DELTA_CONFIG, "w")
 f.write(file_output)
 f.close()
 print(" Success")
 print("\nJOB END: " + datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z"))
except Exception as e:
 print(" Error [" + e + "]")
 print("\nJOB END: " + datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z"))