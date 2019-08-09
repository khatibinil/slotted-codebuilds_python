import boto3
from datetime import datetime

session = boto3.Session(profile_name='niloo-aws')
client = session.client('dynamodb')

##Helper Functions
def get_component_version(component_name):
    """Get version of component, creates version 0.0.0 if component does not exist"""
    region = session.region_name
    table_name = "scm_{}_version_table".format(region)
    response = client.get_item(  TableName=table_name,
            Key={'ComponentName':{'S': component_name}},
            ProjectionExpression='Major, Minor, Patch'
        )
    try:
        return response['Item']
    except KeyError as e:
        print("Item {} does not exist in table.".format(component_name))
        response = client.update_item(  TableName=table_name,
            Key={'ComponentName':{'S': component_name }},
            UpdateExpression="SET Major=:p, Minor=:p, Patch=:p",
            ExpressionAttributeValues={":p": {"N":"0"}},
            ReturnValues='ALL_NEW'
            )
        return response['Attributes']


def update_component_version(component_name):
    """Increment the version for component_name."""
    region = session.region_name
    table_name = "scm_{}_version_table".format(region)
    response = client.update_item( TableName=table_name,
            Key={'ComponentName':{ 'S': component_name }},
            UpdateExpression="ADD Patch :p",
            ExpressionAttributeValues={":p": {"N":"1"}},
            ReturnValues='ALL_NEW'
            )
    return response['Attributes']


def update_component_success_version(component_name, version):
    """Update success_version for component in version table."""
    region = session.region_name
    table_name = "scm_{}_version_table".format(region)
    response = client.update_item( TableName=table_name,
            Key={'ComponentName':{ 'S': component_name }},
            UpdateExpression="SET Successful_Version =  :p",
            ExpressionAttributeValues={
                    ":p" : { "M" : {
                            "Version" : { "S" : version},
	                        "DateUTC" : { "S" : datetime.utcnow().isoformat()}
	                       }}},
            ReturnValues='ALL_NEW'
            )


def generate_version(component_name):
    """Generates new Version for component_name"""

    item_attributes = get_component_version(component_name)
    major = int(item_attributes['Major']['N'])
    minor = int(item_attributes['Minor']['N'])
    patch = int(item_attributes['Patch']['N'])
    current_version = f"{major}.{minor}.{patch}"
    print(f"Current version is {current_version}")

    updated_attributes = update_component_version(component_name)
    new_major = int(updated_attributes['Major']['N'])
    new_minor = int(updated_attributes['Minor']['N'])
    new_patch = int(updated_attributes['Patch']['N'])
    new_version = f"{new_major}.{new_minor}.{new_patch}"
    print(f"New version is {new_version}")

    return new_version

if __name__ == '__main__':
    generate_version()
