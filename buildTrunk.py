import boto3
import json
from botocore.config import Config
from datetime import datetime
import uuid
import ipaddress
import secrets
import string


regionChosen = ''   # Add region if desired
vpcChosen = ''      # Add VPC if desired
subnetChosen = ''   # Add subnet if desired
keypairChosen = ''  # Add keypair if desired
homeIPChosen = ''   # Add home network if desired as xxx.xxx.xxx.xxx/xx

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        serial = obj.isoformat()
        return serial
    raise TypeError("Type not serializable")

def get_secure_random_string(length):
    secure_str = ''.join((secrets.choice(string.ascii_letters) for i in range(length)))
    return secure_str


if not regionChosen:
    print('1. us-east-1')
    print('2. us-west-1')
    regionSelection = int(input('Select Region: '))

    if regionSelection == 1:
        regionChosen = 'us-east-1'
    elif regionSelection == 2:
        regionChosen = 'us-west-1'
    else:
        regionChosen = ''

my_config = Config(
    region_name = regionChosen,
    signature_version = 'v4',
    retries = {
        'max_attempts': 10,
        'mode': 'standard'
    }
)

client = boto3.client('ec2', config=my_config)        

if not vpcChosen:
    response = client.describe_vpcs()

    vpcIDs = ['blank']
    selection = 0

    for i in response['Vpcs']:
        selection = selection + 1
        print (str(selection) + ". " + i['VpcId'] + " - " + i['CidrBlock'])
        vpcIDs.append(i['VpcId'])

    vpcSelection = input('Select VPC: ')
    vpcChosen = vpcIDs[int(vpcSelection)]

if not subnetChosen:
    response = client.describe_subnets(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [vpcChosen]
            }
        ]
    )

    selection = 0
    subnetIDs = ['blank']

    for i in response['Subnets']:
        selection = selection + 1
        print (str(selection) + ". " + i['CidrBlock'] + " - " + i['AvailabilityZone'])
        subnetIDs.append(i['SubnetId'])

    subnetSelection = int(input('Select Subnet: '))
    subnetChosen = subnetIDs[subnetSelection]

if not keypairChosen:
    response = client.describe_key_pairs()
    selection = 0
    keypairIDs = ['blank']

    for i in response['KeyPairs']:
        selection = selection + 1
        print (str(selection) + ". " + i['KeyName'])
        keypairIDs.append(i['KeyName'])

    keypairSelection = int(input('Select KeyPair: '))
    keypairChosen = keypairIDs[keypairSelection]

if not homeIPChosen:
    while True:
        try:
            homeIPSelection = str(input('Enter public IPv4 Address of home network: '))
            if ipaddress.ip_address(homeIPSelection):
                homeIPChosen = homeIPSelection+'/32'
                break
            else:
                print("Please ensure IPv4 address is valid in format xxx.xxx.xxx.xxx")
        except ValueError:
            print("Provide an integer value...")
            continue

print ('Region: ' + regionChosen)
print ('VPC: ' + vpcChosen)
print ('Subnet ' + subnetChosen)
print ('Keypair: ' + keypairChosen)
print ('Creating Voice Connector Trunk')

client = boto3.client('chime', config=my_config)

response = client.search_available_phone_numbers(
    # AreaCode='string',
    # City='string',
    # Country='string',
    State='IL',
    # TollFreePrefix='string',
    MaxResults=1,
    # NextToken='string'
)

phoneNumberToOrder = response['E164PhoneNumbers'][0]

print ('Phone Number: ' + phoneNumberToOrder)

response = client.create_phone_number_order(
    ProductType='VoiceConnector',
    E164PhoneNumbers=[
        phoneNumberToOrder,
    ]
)

response = client.create_voice_connector(
    Name='Trunk' + str(uuid.uuid1()),
    AwsRegion=regionChosen,
    RequireEncryption=False
)

voiceConnectorId = response['VoiceConnector']['VoiceConnectorId']
outboundHostName = response['VoiceConnector']['OutboundHostName']
password = get_secure_random_string(8)

print('Password: ' + password)
print('VoiceConnectorID: ' + voiceConnectorId)
print('OutboundHostName: ' + outboundHostName)
now = datetime.now()
current_time = now.strftime("%H:%M:%S")
print("Current Time =", current_time)
print ('Creating stack... please be patient, this could take several minutes while it deploys')

client = boto3.client('cloudformation', config=my_config)

with open('instance.yaml', 'r') as cf_file:
    cft_template = cf_file.read()

response = client.create_stack(
    StackName=voiceConnectorId,
    TemplateBody=cft_template,
    Parameters=[
        {
            'ParameterKey': 'VpcId',
            'ParameterValue': vpcChosen                              
        },
        {
            'ParameterKey': 'HomeIP',
            'ParameterValue': homeIPChosen
        },
        {
            'ParameterKey': 'SubnetId',
            'ParameterValue': subnetChosen
        },
        {
            'ParameterKey': 'KeyPair',
            'ParameterValue': keypairChosen
        },
        {
            'ParameterKey': 'PhoneNumber',
            'ParameterValue': phoneNumberToOrder
        },
        {
            'ParameterKey': 'Password',
            'ParameterValue': password
        },
        {
            'ParameterKey': 'VoiceConnectorHostName',
            'ParameterValue': outboundHostName
        }
    ])
waiter = client.get_waiter('stack_create_complete')
waiter.wait(StackName=voiceConnectorId)

response = client.describe_stacks(StackName=voiceConnectorId)

cfOutput = response['Stacks'][0]['Outputs']

for i in cfOutput:
    if i['OutputKey'] == 'AsteriskServerIP':
        serverIP = i['OutputValue']

serverIPCIDR = serverIP + '/32'

print('Server IP: ' + serverIP)
print('Server IP CIDR: ' + serverIPCIDR)

client = boto3.client('chime', config=my_config)

response = client.put_voice_connector_origination(
    VoiceConnectorId=voiceConnectorId,
    Origination={
        'Routes': [
            {
                'Host': serverIP,
                'Port': 5060,
                'Protocol': 'UDP',
                'Priority': 1,
                'Weight': 1
            },
        ],
        'Disabled': False
    }
)

# print(response)

response = client.put_voice_connector_termination(
    VoiceConnectorId=voiceConnectorId,
    Termination={
        'CpsLimit': 1,
        'CallingRegions': [
            'US',
        ],
        'CidrAllowedList': [
            serverIPCIDR,
        ],
        'Disabled': False
    }
)

# print(response)

response = client.associate_phone_numbers_with_voice_connector(
    VoiceConnectorId=voiceConnectorId,
    E164PhoneNumbers=[
        phoneNumberToOrder,
    ],
    ForceAssociate=True
)

# print(response)
now = datetime.now()
current_time = now.strftime("%H:%M:%S")
print("Current Time =", current_time)
print ('Asterisk and Voice Connector built')