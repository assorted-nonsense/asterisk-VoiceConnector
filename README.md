All *Chosen variables in buildTrunk.py can be configured with your specific information for easier deployment.  Otherwise, the script will determine the information required to build.  This must be built in an existing VPC.  If no homeIP is chosen, it will be open to 0.0.0.0/0

This script will deploy and configure an Asterisk server in a predefined VPC.  THIS DEPLOYMENT IS SLOW.  Please be patient as the Asterisk is compiled and configured.  This can take 10+ minutes.  You can log in to server and monitor status by sshing to servier and executing:
tail -f /var/log/cloud-init-output.log

A limit of 3 Trunk Groups is in place on Chime Voice Connector.  If trying to build another Voice Connector above this, the script will fail.

This script will procure a random telephone number from Illinois as part of the deployment and associate with the Voice Connector that is built.

The output contains vital information for configuring your SIP Client.  For example:

Phone Number: +12246005344
VoiceConnectorID: bih7c1yatt5oahoridjaua
Server IP: 54.227.249.70
Password: xxxxxxxxx

When configuring SIP Client:
User ID: +12246005344
Domain: 54.227.249.70
Password: xxxxxxxxx
Topology: ICE/STUN
STUN Server: stun.l.google.com:19302
Transport: UDP
SRTP: No

