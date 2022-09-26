# Author: AAnkers
# Date: 26-Sep-2022
# Description: Email Azure Script Output files to interested parties
import smtplib
import email
import datetime
import os
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Define constants
SMTP_SERVER = 'smtp.yourcompany.com' # SMTP Server
EMAIL_FROM = 'Script on Server1234 <script@server1234.yourcompany.com>' # Email From Address
EMAIL_TO = ['youremail@yourcompany.com'] # Email To Addresses
EMAIL_ATTACHMENTS = ['/opt/scripts/azure-json-ip-srx-checker/azure_srx_delta_config.txt', '/opt/scripts/azure-json-ip-srx-checker/checker.log'] # Email attachment files
# Detect body and subject based on if delta config exists
if os.path.getsize('/opt/scripts/azure-json-ip-srx-checker/azure_srx_delta_config.txt') > 0:
 EMAIL_SUBJECT = 'ACTION REQUIRED - Azure IP Address to SRX Generator run ' + datetime.datetime.now().strftime('%d %b %Y') # Email Subject line
 EMAIL_BODY = 'This is the export file from the Azure IP Address to SRX Configuration Generator.\r\n\r\nChange IS REQUIRED and has been DETECTED.\r\n\r\nPlease load these onto the following Firewalls:\r\n - FIREWALL-NAME-HERE\r\n\r\n- Azure IP to SRX Generator Script\n' # Email Body message
else:
 EMAIL_SUBJECT = 'No Change - Azure IP Address to SRX Generator run ' + datetime.datetime.now().strftime('%d %b %Y') # Email Subject line
 EMAIL_BODY = 'This is the export file from the Azure IP Address to SRX Configuration Generator.\r\n\r\nNo change has been detected.\r\n\r\nPlease review these against the following Firewalls:\r\n - FIREWALL-NAME-HERE\r\n\r\n- Azure IP to SRX Generator Script\n' # Email Body message

# Functions
# Encode attachment as MIME Base64
def getAttachmentData(files, message):
 # Initialise variables
 part = ''
 
 # Loop through each input file
 for file in files:
  # Open Attachment file in binary mode
  with open(file, "rb") as attachment:
   # Add file as application/octet-stream
   # Email client can usually download this automatically as attachment
   part = MIMEBase("application", "octet-stream")
   part.set_payload(attachment.read())

  # Encode file in ASCII characters to send by email    
  encoders.encode_base64(part)

  # Extract filename from path
  filename = file.split('/')[-1]
  
  # Add header as key/value pair to attachment part
  part.add_header(
   "Content-Disposition",
   f"attachment; filename= {filename}",
  )
  # Add part to message
  message.attach(part)

# Main program
# Create a multipart message and set headers
message = MIMEMultipart()
message.preamble = 'This is a multi-part message in MIME format.\n'
message.epilogue = ''
message["From"] = EMAIL_FROM
message["To"] = ", ".join(EMAIL_TO)
message["Subject"] = EMAIL_SUBJECT

# Add body to email
message.attach(MIMEText(EMAIL_BODY, "plain"))

# Add attachments to message and convert message to string
getAttachmentData(EMAIL_ATTACHMENTS, message)
text = message.as_string()

# Send email via SMTP Server
print("JOB START: " + datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z") + "\n")
try:
 server = smtplib.SMTP(SMTP_SERVER, 25)
 #server.set_debuglevel(1)
 server.connect(SMTP_SERVER, 25)
 server.sendmail(EMAIL_FROM, EMAIL_TO, text)
 server.quit()
 print("Email successfully sent to " + str(EMAIL_TO))
 print("\nJOB END: " + datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z"))
except smtplib.SMTPException as error:
 print(error)
 print("\nJOB END: " + datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z"))
