import boto3
import subprocess
import os
import time

def create_session(region, access_key, secret_access_key, session_token):
    session = boto3.Session(
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_access_key,
        aws_session_token=session_token,
    )
    return session

def promote_secondary_replica(client, replica_identifier):
    try:
        response = client.promote_read_replica(DBInstanceIdentifier=replica_identifier)
        print(f"Promoting read replica {replica_identifier}...")
    except Exception as e:
        print(f"Error promoting read replica: {e}")

def modify_instance_for_multiaz(client, db_identifier):
    try:
        response = client.modify_db_instance(
            DBInstanceIdentifier=db_identifier,
            MultiAZ=True,
            ApplyImmediately=True
        )
        print(f"Modifying {db_identifier} for Multi-AZ...")
    except Exception as e:
        print(f"Error modifying instance for Multi-AZ: {e}")

def create_and_associate_groups(client, db_identifier):
    try:
        response = client.create_option_group(
            OptionGroupName=f"{db_identifier}-option-group",
            EngineName="sqlserver-ee",
            MajorEngineVersion="15.00",
            OptionGroupDescription=f"Option group for {db_identifier}"
        )
        response = client.create_db_parameter_group(
            DBParameterGroupName=f"{db_identifier}-parameter-group",
            Description=f"Parameter group for {db_identifier}"
        )
        response = client.modify_db_instance(
            DBInstanceIdentifier=db_identifier,
            OptionGroupName=f"{db_identifier}-option-group"
        )
        response = client.modify_db_instance(
            DBInstanceIdentifier=db_identifier,
            DBParameterGroupName=f"{db_identifier}-parameter-group"
        )
        print(f"Creating and associating option and parameter groups for {db_identifier}...")
    except Exception as e:
        print(f"Error creating and associating groups: {e}")

def handle_disaster_recovery(primary_client, replica_client, primary_db_identifier, replica_identifier):
    print(f"Primary RDS instance {primary_db_identifier} is not available. Initiating disaster recovery...")
    promote_secondary_replica(replica_client, replica_identifier)
    time.sleep(600)
    modify_instance_for_multiaz(replica_client, replica_identifier)
    create_and_associate_groups(replica_client, replica_identifier)

def main():
    primary_region = "eu-west-1"
    replica_region = "eu-central-1"
    access_key = ""
    secret_access_key = ""
    session_token = ""

    primary_session = create_session(primary_region, access_key, secret_access_key, session_token)
    replica_session = create_session(replica_region, access_key, secret_access_key, session_token)
    
    dr_condition = input("Is the DR condition activated? (yes/no): ")
    if dr_condition.lower() == "yes":
        primary_db_identifier = input("Enter the primary RDS instance identifier: ")
        replica_db_identifier = input("Enter the read replica identifier: ")
        handle_disaster_recovery(primary_session.client('rds'), replica_session.client('rds'), primary_db_identifier, replica_db_identifier)
    else:
        print("DR condition is not activated. No actions taken.")

if __name__ == "__main__":
    main()

# We need to change the condition for DR
# Add if else condition for different modes like mOdifying and maintainance
# Route53 cname record updation
# After the completion of DR check if the RDS instance is available. SES Service
# Telnet command to check 1433 port 
# telnet dns name port number --> Verification step  


# subprocess.call(["terraform", "init", "-reconfigure", "-backend-config=bucket=terraform-patching-statefiles", "-backend-config=key=RDS/Aurora-Postgresql/Cluster/terraform.tfstate", "-backend-config=region=eu-west-1"], cwd=terraform_directory)