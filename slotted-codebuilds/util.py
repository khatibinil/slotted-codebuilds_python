"""Utilities for codebuild."""
import yaml
import uuid
import zipfile
import pathlib
import boto3

AWS_ACCOUNT_ID = ""
AWS_REGION = "us-west-2"
AWS_SEC_REGION = "us-east-1"
SCM_BUCKET = "deployment-packages-w2"
SCM_SEC_BUCKET = "deployment-packages-e1"

session = boto3.Session(profile_name='niloo-aws')
cw_client = session.client('logs')


def update_buildspec_template(buildspec_tmpl, env_vars):
    """Update buildspec template file and add environment variables based on input argumets."""
    with open(buildspec_tmpl, 'r') as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
        data['env']['variables'] = env_vars
    with open('buildspec.yml', 'w') as f:
        yaml.dump(data, f)
    return data

def compress_temp_package(file_path):
    """Create zip file containing file_path to be used as slotted codebuild source."""

    zip_path = pathlib.Path(f'{uuid.uuid1()}.zip')
    temp_zip = zipfile.ZipFile(zip_path, 'w')
    temp_zip.write(file_path,compress_type=zipfile.ZIP_DEFLATED)
    temp_zip.close()
    file_path.unlink()
    return zip_path

def pull_cloudwatch_logs(cw_log):
    """Import logs for codebuild from cloudwatch logs."""

    #try:
    cw_response = cw_client.get_log_events(
                logGroupName=cw_log['groupName'],
                logStreamName=cw_log['streamName'])
    events = cw_response['events']
    log_message=""
    for e in events:
        log_message += e['message']
    print(log_message)
    #except:
    #    print("Reading codebuild logs from cloudwatch threw an exception")


def update_ssm_values(slot_family,component_name,version):
    """Publish versions for artifact in ssm."""

    if slot_family == "nodejs" or "dotnet" or "php":
        #s3_key_prefix = f"{env_vars[S3_KEY_PREFIX]}/{component_name}"
        ssm_name = f"/fams/scm_packages/s3/{component_name}"
        if version:
            ssm_value = f"s3://{SCM_BUCKET}/{component_name}-{version}.zip"
            ssm_sec_value = f"s3://{SCM_SEC_BUCKET}/{component_name}-{version}.zip"
        else:
            ssm_value = f"s3://{SCM_BUCKET}/{component_name}.zip"
            ssm_sec_value = f"s3://{SCM_SEC_BUCKET}/{component_name}.zip"

    elif slot_family == "packer":
        ssm_name = f"/fams/scm_packages/ecr/{component_name}"
        ssm_value = f"{AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com/{component_name}:{version}"
        ssm_sec_value = f"{AWS_ACCOUNT_ID}.dkr.ecr.us-{AWS_SEC_REGION}.amazonaws.com/{component_name}:{version}"

    elif slot_family == "ami":
         ami_name = f"{component_name}@{version}"
         ssm_name = f"/fams/scm_packages/ami/{component_name}"
         ssm_value = find_ami_id(ami_name, AWS_REGION)
         ssm_sec_value = find_ami_id(ami_name, AWS_SEC_REGION)

    #Assume role for sbx and dev account before running ssm put

    ssm_put_parameter(ssm_name,ssm_value,AWS_REGION)
    print(f"Pushed ssm value {ssm_value} to region {AWS_REGION}" )
    ssm_put_parameter(ssm_name,ssm_sec_value,AWS_SEC_REGION)
    print(f"Pushed ssm value {ssm_sec_value} to region {AWS_SEC_REGION}" )


def find_ami_id(ami_name, region):
    #needs to be tested
    ec2 = boto3.resource('ec2', region_name=region)
    response = ec2.images.filter( Filters=[
        {
            'Name': 'name',
            'Values': [ 'ami_name',]
        },
    ])
    return response['Images']['ImageId']

def ssm_put_parameter(ssm_name,ssm_value,region): #add aws_account
    #assume_aws_role(aws_account)
    ssm_client = session.client('ssm', region_name=region)
    ssm_client.put_parameter(Name=ssm_name,
            Value=ssm_value,
            Type='String',
            Overwrite=True)

def assume_aws_role(aws_account):
    """Assumes role based on aws_account passed in order to excutes certain menthods."""
    pass
