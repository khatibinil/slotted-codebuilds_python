# -*- coding: utf-8 -*-

"""Functions for codebuild."""
import boto3
import random
from datetime import datetime
import time as tyme
#import pathlib

session = boto3.Session(profile_name='niloo-aws')
client = session.client('dynamodb')
cb_client = session.client('codebuild')
s3_client = session.client('s3')

SCM_BUCKET  = 'deployment-packages-w2'
SCM_BUCKET_KMS_KEY_ID = "b3a7437b-eb75-4570-ba0c-9cfafaca7815"


def find_open_slot(codebuild_slot, build_component_name):
    """Find Open Slot to run build on for SLOT_FAMILY."""
    table_name = "{}_table".format(codebuild_slot)
    open_slots = client.scan( TableName=table_name,
                FilterExpression="SlotFamily = :s AND attribute_not_exists(DateStarted)" ,
                ExpressionAttributeValues={":s": {"S":codebuild_slot}}
            )

    if len(open_slots['Items']) < 1: #no open_slots avaiable
        cleanup_old_slots(codebuild_slot)
        return
    else:
        target_slot = random.choice(open_slots['Items'])

    if 'Attributes' in target_slot :
        slot_name = target_slot['Attributes']['ComponentName']['S']
        cv =target_slot['Attributes']['cv']['N']
    else:
        slot_name = target_slot['ComponentName']['S']
        cv =target_slot['cv']['N']

    print("Trying to lock {}".format(slot_name))
    response = client.update_item( TableName=table_name,
            Key={'ComponentName':{'S': slot_name }},
            UpdateExpression="ADD cv :p SET DateStarted = :d, InstanceName = :n",
            ExpressionAttributeValues={
                                        ":p" : {"N" : "0.0001" },
                                        ":i" : {"N": cv},
                                        ":d" : {"S" : datetime.utcnow().isoformat() },
                                        ":n" : {"S": build_component_name}
            },
            ConditionExpression='cv = :i',
            ReturnValues='ALL_NEW'
            )
    return response['Attributes']

def cleanup_old_slots(codebuild_slot):
    """Clean Slots that have old failed builds for SLOT_FAMILY."""
    table_name = "{}_table".format(codebuild_slot)
    response = client.scan( TableName=table_name,
                FilterExpression="SlotFamily = :s" ,
                ExpressionAttributeValues={":s": {"S":codebuild_slot}}
            )
    nonrunning_slots=[]
    for item in response['Items']:
        time_delta = datetime.utcnow() - datetime.strptime(item['DateStarted']['S'],'%Y-%m-%dT%H:%M:%S.%f')
        if 'DateStarted' not in item or time_delta.total_seconds() > 60: #or diff of now with start time is greated than 1 min
            if 'InstanceID' not in item:
                nonrunning_slots.append(item)
            else:
                codebuild_id = item['InstanceID']['S']
                cb_res = cb_client.batch_get_builds( ids=[codebuild_id])
                if len(cb_res) < 1 :
                    nonrunning_slots.append(item)
                elif cb_res['builds'][0]['buildComplete']:
                    nonrunning_slots.append(item)

    for slot in nonrunning_slots:
        response = client.update_item( TableName=table_name,
                 Key={ 'ComponentName': { 'S': slot['ComponentName']['S']}},
                     UpdateExpression=" REMOVE DateStarted, InstanceID, InstanceName SET cv = :z",
                     ExpressionAttributeValues={
                                                    ":i" : { "N" : slot['cv']['N']},
                                                    ":z" : { "N" :"0"}},
                     ConditionExpression='cv = :i'
                 )

def get_build_results(codebuild_id):
    build_results={}
    cb_res = cb_client.batch_get_builds( ids=[codebuild_id])
    build_results["build_status"] = cb_res['builds'][0]['buildStatus']
    build_results["build_logs"] = cb_res['builds'][0]['logs']
    return build_results

def run_slotted_codebuild(codebuild_slot,component_name,temp_package):
    """Trigger Slotted Codebuild"""
    table_name = "{}_table".format(codebuild_slot)
    print(f"Finding a slot for build {component_name}")
    target_slot = find_open_slot(codebuild_slot, component_name)

    retry_count = 1
    while not target_slot and retry_count <= 10:
        print(f"Unable to lock a slot. Retrying ({retry_count})...")
        tyme.sleep(random.randint(5,20))
        target_slot = find_open_slot(codebuild_slot, component_name)
        retry_count += 1
    if not target_slot and retry_count > 10:
        raise Exception(f"Unable to find open slot after 10 retries.")

    cb_project =  target_slot['ComponentName']['S']
    print(f"Locked {cb_project}")

    #clear old InstanceID
    response = client.update_item( TableName=table_name,
             Key={ 'ComponentName':{ 'S': cb_project  }},
             UpdateExpression="REMOVE InstanceID",
             ReturnValues='ALL_NEW'
             )
    #trigger_slot_job
    print(f"Starting {cb_project}")
    s3_key = "codebuild/source/{}.zip".format(cb_project)
    #s3.meta.client.upload_file(Filename=str(temp_package),
    s3_client.upload_file(Filename=str(temp_package),
              Bucket=SCM_BUCKET,
              Key= s3_key,
              ExtraArgs={
                 "ServerSideEncryption": "aws:kms",
                 "SSEKMSKeyId": SCM_BUCKET_KMS_KEY_ID
               }
              )
    temp_package.unlink() #delete temp package

    cb_responce = cb_client.start_build(projectName=cb_project)
    codebuild_id = cb_responce['build']['id']

    #update instanceID in codebuild-slot-table
    response = client.update_item( TableName=table_name,
             Key={ 'ComponentName':{'S': cb_project }},
             UpdateExpression="SET InstanceID = :i",
             ExpressionAttributeValues={ ":i" : { "S" : codebuild_id} },
             ReturnValues='ALL_NEW'
             )

    # wait for build job to complete
    build_results = get_build_results(codebuild_id)
    print(f'{codebuild_id} - {build_results["build_status"]}')
    while build_results["build_status"] == "IN_PROGRESS":
        tyme.sleep(10)
        build_results = get_build_results(codebuild_id)
        print(f'{codebuild_id} - {build_results["build_status"]}')

    print(f'Releasing {cb_project}')

    response = client.update_item( TableName=table_name,
             Key={ 'ComponentName':{'S': cb_project }},
             UpdateExpression="REMOVE DateStarted, InstanceID, InstanceName SET cv = :z",
             ExpressionAttributeValues={":z" : { "N" :"0"} },
             ReturnValues='ALL_NEW'
             )

    return build_results
