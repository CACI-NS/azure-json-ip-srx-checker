# Azure JSON IP Feed to Juniper SRX Checker
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/ansicolortags.svg)](https://pypi.python.org/pypi/ansicolortags/) [![GitHub license](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/CACI-NS/azure-json-ip-srx-checker/blob/main/LICENSE)

> Need help getting from NetDevOops to NetDevOps? Learn about how [Network Automation and NetDevOps at CACI](https://info.caci.co.uk/network-automation-devops-caci) can help you on your journey

## About
Azure JSON IP Feed to Juniper SRX Checker is intended to be run on a periodic (i.e. daily) basis to check for updates/change/deletions made by Microsoft to their Azure IP Address Ranges as per the Microsoft-published [Azure IP Ranges and Service Tags – Public Cloud](https://www.microsoft.com/en-us/download/details.aspx?id=56519) JSON feed and convert into Junos SRX-comptaible Security Policy syntax/configuration.

The intent of this is to be used with a predefined "opinionated" format of Juniper SRX Firewall Policy/ACL statements that allows access (typically via either Microsoft ExpressRoute or Public Internet) to predefined allowed parts of the Azure Cloud, for instance:
- [Azure SQL](https://azure.microsoft.com/en-gb/products/azure-sql/)
- [Azure CosmosDB](https://azure.microsoft.com/en-gb/products/cosmos-db/)
- [Azure Storage](https://azure.microsoft.com/en-gb/products/category/storage/)

Where the following mappings are true (as defined within the checker.py file):

| Azure PaaS | SRX Address Book |
| ---------- | ---------------- |
| Azure SQL | AZURE_SQL_GLOBAL |
| Azure CosmosDB | AZURE_COSMOSDB_GLOBAL |
| Azure Storage | AZURE_STORAGE_GLOBAL |

Others are easily added to the checker.py script; these three are provided as commonly-used examples,

### Example opinionated Junos Security Policy
An example Junos SRX ACL for Azure SQL might look like (the Source IPs/Ports may differ depending on your IT Security Policies):
```Junos SRX
set security policies from-zone Production to-zone ExpressRoute-Public policy EXPRESSROUTE-AZURE-CLOUD-SQL description "Allow Production WAN to Azure SQL via ExpressRoute on SQL Database Ports"
set security policies from-zone Production to-zone ExpressRoute-Public policy EXPRESSROUTE-AZURE-CLOUD-SQL match source-address PROD_10.0.0.0/8
set security policies from-zone Production to-zone ExpressRoute-Public policy EXPRESSROUTE-AZURE-CLOUD-SQL match destination-address AZURE_SQL_GLOBAL
set security policies from-zone Production to-zone ExpressRoute-Public policy EXPRESSROUTE-AZURE-CLOUD-SQL match application junos-ping
set security policies from-zone Production to-zone ExpressRoute-Public policy EXPRESSROUTE-AZURE-CLOUD-SQL match application junos-ms-sql
set security policies from-zone Production to-zone ExpressRoute-Public policy EXPRESSROUTE-AZURE-CLOUD-SQL match application TCP_3306
set security policies from-zone Production to-zone ExpressRoute-Public policy EXPRESSROUTE-AZURE-CLOUD-SQL then permit
```

### Generated Outcome
The idea is that the "AZURE_SQL_GLOBAL" Destination Address Book Object is then kept updated with only the current relevant IPv4 Address Space which Microsoft uses for Azure SQL, as per the [Microsoft Azure JSON Feed](https://www.microsoft.com/en-us/download/details.aspx?id=56519).

### Generated Policy Deployment
The generated SRX syntax would still need to be deployed manually, or via other means (such as NMS, OSS, CI/CD Pipeline) into the relevant Juniper SRX Firewall Units. A suggested manual approach to this looks like the below, where `admin` is the SSH RO User for the Junos SRX Firewall with Management IP `10.99.99.99`:
1. Download the generated `azure_srx_delta_config.txt` file to the Network Management Jumpbox (i.e. NetDevOps Box with SSH access to the Juniper SRX)
2. Use SCP to push this file to `/tmp/deploy.txt`:
   1. `scp azure_srx_delta_config.txt admin@10.99.99.99:/tmp/deploy.txt`
3. SSH into the SRX; enter into Config Mode; load the config & and commit to the SRX:
   1. `ssh admin@10.99.99.99`
   2. `conf`
   3. `load set /tmp/deploy.txt`
   4. `commit check`
       1. Assuming passes without syntax errors (otherwise fix these): 
   5. `commit`
4. Check the Policy pushed and updated modified Microsoft Public IP Addresses:
    1. `show security policy policy-name EXPRESSROUTE-AZURE-CLOUD-SQL detail`

## Requirements
- Python 2.7 or 3.4+
   - Netmiko
- Direct Internet Access or HTTP Proxy
  - To periodically download the [Microsoft Azure JSON Feed](https://www.microsoft.com/en-us/download/details.aspx?id=56519)
- (Optional) SMTP Server
  - To periodically email the Output Log (human-readable detected IP Address changes) and Delta Config (SRX delta configuration) to a Network Engineer

## Executables
| Name | Type | Run Order | Description |
| ---- | ---- | --------- | ----------- |
| checker.py | Python Script | First | Performs the logic to download, check and delta the [Microsoft Azure JSON Feed](https://www.microsoft.com/en-us/download/details.aspx?id=56519) against the lastest-downloaded SRX Azure-specific ACL configurations |
| mailer.py | Python Script | Second | Emails the Output Log and Delta Config to nominated email addresses |

## Outputs
| Name | Type | Example Output | Description |
| ---- | ---- | -------------- | ----------- |
| srx_config_current.txt | Text (Junos SRX) | `set security policy...` | Latest-pulled Junos SRX Security Policy ACL config (relevant to "AZURE_..." only) |
| azure_srx_delta_config.txt | Text (Junos SRX) | `set security policy...` | Generated Junos SRX Security Policy Address Book add/delete ACL configs |
| checker.log | Text (Logfile) | `Downloading latest Microsoft Azure JSON File` | Human-readable result of execution of the checker.py script, including detected added/deleted Azure IPv4 Addresses |
| mailer.log | Text (Logfile) | `Email successfully sent to...` | Human-readable result of execution of mailer.py script, including email address(es) outputs were sent to |

## Installation
### Download
Depending on whether your Network Management Jumpbox has Direct/Proxy Internet Access, either:
- Git clone this repo into the desired folder (i.e. assuming Linux OS, maybe into `/opt/scripts/azure-json-ip-srx-checker/`)
- Download this repo as a ZIP and unzip into the desired folder on your Network Management Jumpbox

The example `log` and `txt` files supplied will be overwritten on the first run of the script.

### Python Modules
The following PyPI Modules are required as per `requirements.txt`:
- Netmiko

Install these on the Network Management Jumpbox with:

`pip install -r requirements.txt`

### Environment Variables
All relevant locally-significant Environment Variables are stored within ALL_CAPS constants specified towards the top of each Python executable script, these will need to be modified prior to first-run to your specific Environment (i.e. your Company's HTTP Proxy Server/User/Pass, or specific Installation Directory etc). The important Constants to change are:
| Script | Variable | Example | Description |
| ------ | -------- | ------- | ----------- |
| checker.py | OUTPUT_JSON_FILE | `/opt/scripts/azure-json-ip-srx-checker/Azure_IPs.json` | Change the path to the Linux/Windows OS directory you installed to |
| checker.py | OUTPUT_SRX_CURRENT | `/opt/scripts/azure-json-ip-srx-checker/srx_config_current.txt` | Change the path to the Linux/Windows OS directory you installed to |
| checker.py | OUTPUT_DELTA_CONFIG | `/opt/scripts/azure-json-ip-srx-checker/azure_srx_delta_config.txt` | Change the path to the Linux/Windows OS directory you installed to | 
| checker.py | AZURE_SRX_MAP | `{'Sql':'AZURE_SQL_GLOBAL'}` | Add mappings for each Azure Service you want to check (Names defined by Microsoft in the JSON file) |
| checker.py | HTTP_PROXY | `{"https": "http://proxyuser:proxypassword@proxy.yourcompany.com:8080"}` | Change for your specific Corporate Proxy details |
| checker.py | SSH_IP | `10.99.99.99` | Change for your SRX Management IP Address |
| checker.py | SSH_USER | `admin` | Change for your SRX SSH Username (Readonly required) |
| checker.py | SSH_PASS | `Password1234` | Change for your SRX SSH Password (Readonly required) |
| mailer.py | SMTP_SERVER | `smtp.yourcompany.com` | Change for your specific Corporate SMTP Server details |
| mailer.py | EMAIL_FROM | `Script on Server1234` | Change for your specific Corporate SMTP Server Sender details |

Other Constants are also commented within the Python executable scripts themselves, if required to be changed for your specific Environment.

## Scheduling
This script is designed to be run periodically (i.e. Daily), as per the order specified earlier in the [Executables](#Executables) section of this README. Depending on the OS (i.e. Linux or Windows) your Network Management Jumpbox uses will depend on whether this is scheduled as:
- Windows
  - Scheduled Tasks
- Linux
  - Cron job

### Example Linux Crontab (/etc/crontab)
_Note: This assumes the script is installed to /opt/scripts/azure-json-ip-srx-checker/, runs lazily as root, and you want to send the post-run email daily at 08:30_
```Bash
25 8 * * * root /opt/scripts/azure-json-ip-srx-checker/checker.py > /opt/scripts/azure-json-ip-srx-checker/checker.log >/dev/null 2>&1
30 8 * * * root /opt/scripts/azure-json-ip-srx-checker/mailer.py > /opt/scripts/azure-json-ip-srx-checker/mailer.log >/dev/null 2>&1
```

## Resources
* [Microsoft Azure JSON Feed](https://www.microsoft.com/en-us/download/details.aspx?id=56519)
* [Juniper Security Policies User Guide for Security Devices](https://www.juniper.net/documentation/us/en/software/junos/security-policies/topics/topic-map/security-policy-configuration.html)