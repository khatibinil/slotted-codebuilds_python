import boto3
import click
from dynamoDb import DynamoDBManager

session = boto3.Session(profile_name='niloo-aws')
dynamodb_manager = DynamoDBManager(session)

###Helper Functions

@click.argument('slot_family')
def generate_arg_list(slot_family):
    switch (slot_family) {
                case 1:  slot_family = "codebuild-nodejs-slot";
                         break;
                case 2:  slot_family = "codebuild-dotnet-slot";
                         break;
                case 3:  slot_family = "codebuild-ami-slot";
                         break;
                case 4:  slot_family = "codebuild-packer-slot";
                         break;
            }

@click.argument('component_name')
def generate_version(component_name):
    """Generates new Version for component_name"""
    item_attributes = dynamodb_manager.get_component_version(component_name)
    current_version = "{0}.{1}.{2}".format(int(item_attributes['Major']), int(item_attributes['Minor']), int(item_attributes['Patch']))
    print("Current version is {}".format(current_version))
    updated_attributes = dynamodb_manager.update_component_version(component_name)
    version = "{0}.{1}.{2}".format(int(updated_attributes['Major']), int(updated_attributes['Minor']), int(updated_attributes['Patch']))
    print("New version is {}".format(version))

#Helper functions ###

@click.group()
def cli():
    """slotted-codebuild triggers codebuild projects on predefined CodeBuild slots based on input arguments"""

@cli.command('s3-codebuild')
#@command.arguments()
def s3_codebuild():
    """Trigger slotted codebuild that publish artifacts to S3 bucket."""
    pass



if __name__ == "__main__" :
    cli()
