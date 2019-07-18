# -*- coding: utf-8 -*-
from pathlib import Path

"""Classes for S3 buckets."""

class DynamoDBManager:
    """Manage DynamoDB functions."""

    def __init__(self, session):
        """Create a Bucket manager."""
        self.session = session
        self.dynamodb = self.session.resource('dynamodb')


    def get_component_version(self,component_name):
        """Get version of component, creates version 0.0.0 if component does not exist"""
        region = self.session.region_name
        table = self.dynamodb.Table("scm_{}_version_table".format(region))
        response = table.get_item( Key={
                'ComponentName': component_name
            },
            ProjectionExpression='Major, Minor, Patch'
            )
        try:
            return response['Item']
        except KeyError as e:
            print("Item {} does not exist in table.".format(component_name))
            response = table.update_item( Key={
                    'ComponentName': component_name
                },
                UpdateExpression="SET Major=:p, Minor=:p, Patch=:p",
                ExpressionAttributeValues={":p": 0},
                ReturnValues='ALL_NEW'
                )
            return response['Attributes']


    def update_component_version(self, component_name):
        """Update the path version of the give component"""
        region = self.session.region_name
        table = self.dynamodb.Table("scm_{}_version_table".format(region))
        response = table.update_item( Key={
                    'ComponentName': component_name
                },
                UpdateExpression="ADD Patch :p",
                ExpressionAttributeValues={":p": 1},
                ReturnValues='ALL_NEW'
                )
        return response['Attributes']
