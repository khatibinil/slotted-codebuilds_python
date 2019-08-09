#import boto3
import click
import pathlib
import util
import codebuild
import versionManager

@click.group()
def cli():
    """slotted-codebuild triggers codebuild projects on predefined CodeBuild slots based on input arguments"""

@cli.command('s3-codebuild')
@click.option('--component_name', 'component_name', required=True)
@click.option('--repo', 'repo', required=True)
@click.option('--project_path', 'project_path', required=True)
@click.option('--slot_family', 'slot_family',required=True, type=click.Choice(['dotnet','nodejs', 'php']))
@click.option('--s3_key_prefix', 's3_key_prefix', default="codebuild/packages/lambda")
@click.option('--branch', 'branch')
@click.option('--auto_version', default=True, type=bool)
def s3_codebuild(component_name, repo, project_path, slot_family, s3_key_prefix, branch, auto_version):
    """Trigger slotted codebuild that publish artifacts to S3 bucket."""
    #version = util.generate_version(component_name)
    updateSSM= True
    env_vars={}
    env_vars["PACKAGE_NAME"] = component_name
    env_vars["REPO"] = repo
    env_vars["PROJECT_PATH"] = project_path
    env_vars["S3_KEY_PREFIX"] = s3_key_prefix
    if branch:
        env_vars["BRANCH"] = branch
        updateSSM= False
    if auto_version:
        version = versionManager.generate_version(component_name)
        env_vars["PACKAGE_VERSION"] = version

    execute_build_process(slot_family,component_name,env_vars,updateSSM, version)

@cli.command('packer-codebuild')
@click.option('--component_name', 'component_name', required=True)
@click.option('--repo', 'repo', required=True)
@click.option('--project_path', 'project_path', required=True)
@click.option('--branch', 'branch')
@click.option('--s3_package_path', 's3_package_path')
def s3_codebuild(component_name, repo, project_path, branch, s3_package_path):
    """Trigger slotted codebuild that publish artifacts to S3 bucket."""
    #version = util.generate_version(component_name)
    updateSSM= True
    slot_family = "packer"
    env_vars={}
    env_vars["ECR_NAME"] = component_name
    env_vars["REPO"] = repo
    env_vars["PROJECT_PATH"] = project_path
    env_vars["PACKAGE_PATH"] = s3_package_path
    version = versionManager.generate_version(f'{component_name}_container')
    env_vars["VERSION_TAG"] = version
    if branch:
        env_vars["BRANCH"] = branch
        updateSSM= False

    #check if we need KMS_ARN environment variable passed in

    execute_build_process(slot_family,component_name,env_vars,updateSSM, version)

@cli.command('ami-codebuild')
@click.option('--component_name', 'component_name', required=True)
@click.option('--repo', 'repo', required=True)
@click.option('--project_path', 'project_path', required=True)
@click.option('--branch', 'branch')
def s3_codebuild(component_name, repo, project_path, branch):
    """Trigger slotted codebuild that publish artifacts to S3 bucket."""
    #version = util.generate_version(component_name)
    updateSSM= True
    slot_family = "ami"
    env_vars={}
    env_vars["REPO"] = repo
    env_vars["PROJECT_PATH"] = project_path
    version = datetime.utcnow().isoformat()
    env_vars["VERSION"] = version
    if branch:
        env_vars["BRANCH"] = branch
        updateSSM= False

    execute_build_process(slot_family,component_name,env_vars,updateSSM, version)

@cli.command('cicd-codebuild')
@click.option('--pipeline_id', 'pipeline_id', required=True)
@click.option('--app_name', 'app_name', required=True)
@click.option('--repo', 'repo', required=True)
@click.option('--project_path', 'project_path', required=True)
@click.option('--targetAwsProfile', 'targetAwsProfile', required=True, default="sbx")
@click.option('--targetAwsRegion', 'targetAwsRegion', required=True, default="us-west-2")
@click.option('--targetColorOverride', 'targetColorOverride')
@click.option('--ladderOverride', 'ladderOverride')
@click.option('--flowOverrride', 'flowOverrride')
@click.option('--tfvarsOverride', 'tfvarsOverride')
def s3_codebuild(component_name, repo, project_path, slot_family, s3_key_prefix, branch, auto_version):
    """Trigger slotted codebuild that publish artifacts to S3 bucket."""
    #version = util.generate_version(component_name)
    updateSSM= False
    slot_family= "cicd"
    env_vars={}
    env_vars["PIPELINE_ID"] = pipeline_id
    env_vars["APP_NAME"] = app_name
    env_vars["REPO"] = repo
    env_vars["PROJECT_PATH"] = project_path
    env_vars["TARGET_AWS_PROFILE"] = targetAwsProfile
    env_vars["TARGET_AWS_REGION"] = targetAwsRegion
    env_vars["TARGET_COLOR_OVERRIDE"] = targetColorOverride
    env_vars["LADDER_OVERRIDE"] = ladderOverride
    env_vars["FLOW_OVERRIDE"] = flowOverrride
    #write function for converting json to Base64
    env_vars["TFVARS_OVERRIDE_B64JSON"] = tfvarsOverride

    execute_build_process(slot_family,pipeline_id,env_vars,updateSSM)


def execute_build_process(slot_family,component_name,env_vars,updateSSM,version):
    "Function containing build execution process steps."

    codebuild_slot = f'codebuild-{slot_family}-slot'
    buildspec_tmpl = (pathlib.Path.cwd().parent).joinpath('buildspec-templates', f'buildspec-{slot_family}.yml.template')
    util.update_buildspec_template(buildspec_tmpl, env_vars)
    temp_package = util.compress_temp_package(pathlib.Path('buildspec.yml'))
    print(f"temporary pacakge generated: {temp_package}")
    build_results = codebuild.run_slotted_codebuild(codebuild_slot,component_name,temp_package)

    if build_results["build_status"] == "SUCCEEDED":
        if version: versionManager.update_component_success_version(component_name,version)
        if updateSSM:
            if slot_family == "nodejs" or "dotnet" or "php":
                component_name = f"{env_vars['S3_KEY_PREFIX']}/{component_name}"
            util.update_ssm_values(slot_family, component_name,version)

    # Pull build logs from Cloudwatch
    cw_log = build_results["build_logs"]
    util.pull_cloudwatch_logs(cw_log)

    print(f"Build completed with status {build_results['build_status']}.")


if __name__ == "__main__" :
    cli()
