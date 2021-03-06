import boto3
import time
from boto3.dynamodb.conditions import Key

db = boto3.client('dynamodb')
dynamodb = boto3.resource('dynamodb')
dynamo_table = 'Example-NACLs' . #TODO fill in the dynamo table name to track NACLs and changes
nacl = boto3.client('ec2')
created = time.ctime()
epoch = str(int(time.time()))
network_acl_id = 'acl-ffffffff'  #TODO fill in the network ACL ID to block (can be automated for multiple public NACLs)
snsclient = boto3.client('sns')
topic_ARN = 'arn:aws:sns:us-east-1:{accountID}:{SNSSubscriptionName}'  # SNS Subscription ARN

"""
Scan table to get data for sorting
"""
print('Loading function')
print('Scanning dynamoDB to find oldest NACL...')


def scan_table(table_name, filter_key=None, filter_value=None):
    """
    Perform a scan operation on table.
    Can specify filter_key (col name) and its value to be filtered.
    """
    table = dynamodb.Table(table_name)

    if filter_key and filter_value:
        filtering_exp = Key(filter_key).eq(filter_value)
        response = table.scan(FilterExpression=filtering_exp)
    else:
        response = table.scan()

    return response


print('Starting JSON extraction...')


def lambda_handler(event, context):
    VpcId = event['detail']['resource']['instanceDetails']['networkInterfaces'][0]['vpcId']
    ipv4address = event['detail']['service'] \
        ['action']['portProbeAction'] \
        ['portProbeDetails'][0]['remoteIpDetails']['ipAddressV4']
    country = event['detail']['service'] \
        ['action']['portProbeAction'] \
        ['portProbeDetails'][0]['remoteIpDetails'] \
        ['country']['countryName']
    cidr = ipv4address + '/32'  # Convert IP address to /32

    print('Found...')
    print('Country: ', country)
    print('IP: ', ipv4address)
    print('CIDR: ', cidr)

    """
    Compare all rules in DB and determine oldest
    """

    table_data = scan_table(dynamo_table)['Items']
    a = 40000000000  # insanely large epoch number in the year 3237 to filter dates
    rule_num = ''
    for value in table_data:
        if int(value['CreatedEpoch']) < a:
            a = int(value['CreatedEpoch'])
            rule_num = str(value['RuleNum'])

    if rule_num == 100:
        rule_num = str(61)

    """
    Write rule to DB
    """
    print('Rule Number to be created: ', rule_num)
    db.put_item(
        TableName=dynamo_table,
        Item={
            'RuleNum': {'N': rule_num, },
            'CIDR': {'S': cidr, },
            'Action': {'S': 'deny', },
            'VpcId': {'S': VpcId, },
            'Created': {'S': created, },
            'CreatedEpoch': {'N': epoch, },
            'CountryOfOrigin': {'S': country, },
        }
    )
    print(db)

    """
    Delete old NACL and create new one
    You can't modify an existing NACL - only create or delete
    """
    print('Delete NACL for rule number ', rule_num)
    # delete oldest NACL
    nacl_response_del = nacl.delete_network_acl_entry(
        Egress=False,
        NetworkAclId=network_acl_id,
        RuleNumber=int(rule_num),
    )
    print(nacl_response_del)

    print('Create NACL to block CIDR: ', cidr)
    # create new NACL
    nacl_response_create = nacl.create_network_acl_entry(
        CidrBlock=cidr,
        Egress=False,
        NetworkAclId=network_acl_id,
        Protocol='-1',
        RuleAction='deny',
        RuleNumber=int(rule_num),
    )
    print(nacl_response_create)

    """
    Send SNS email after complete
    """

    message = 'Guardduty event triggered. \nCountry of origin: {0}\nIP: {1}'.format(country, ipv4address)
    sns_response = snsclient.publish(
        TopicArn=topic_ARN,
        Message=message,
        Subject='Guardduty NACL Lambda Block',
    )

    print(sns_response)
