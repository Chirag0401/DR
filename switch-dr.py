import boto3
import time

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

def promote_secondary_cluster(client, cluster_identifier):
    try:
        response = client.promote_db_cluster(
            DBClusterIdentifier=cluster_identifier
        )
        print(f"Promoting secondary cluster {cluster_identifier}...")
    except Exception as e:
        print(f"Error promoting secondary cluster: {e}")

def modify_cluster_global_settings(client, cluster_identifier):
    try:
        response = client.modify_db_cluster(
            DBClusterIdentifier=cluster_identifier,
            DeletionProtection=False,
            EnableGlobalWriteForwarding=False,
            EnableGlobalReadForwarding=False
        )
        print(f"Modifying cluster {cluster_identifier} global settings...")
    except Exception as e:
        print(f"Error modifying cluster global settings: {e}")

def handle_disaster_recovery(primary_client, secondary_client, primary_cluster_identifier, secondary_cluster_identifier):
    print(f"Primary cluster {primary_cluster_identifier} is not available. Initiating disaster recovery...")
    
    # Promote the secondary cluster to become the new primary
    promote_secondary_cluster(secondary_client, secondary_cluster_identifier)
    time.sleep(600)  # Wait for promotion to complete
    
    # Modify the secondary cluster to remove it from the global database cluster
    modify_cluster_global_settings(secondary_client, secondary_cluster_identifier)
    
    print("Disaster recovery completed successfully.")

def main():
    db_engine = input("Enter the DB engine (AuroraPostgres/MSSQL): ")

    if db_engine.lower() == "aurorapostgres":
        primary_region = "eu-west-1"
        secondary_region = "eu-central-1"
        access_key = ""
        secret_access_key = ""
        session_token = ""
        
        primary_cluster_identifier = input("Enter the primary cluster identifier: ")
        secondary_cluster_identifier = input("Enter the secondary cluster identifier: ")
        
        primary_client = boto3.client('rds', region_name=primary_region, aws_access_key_id=access_key, aws_secret_access_key=secret_access_key, aws_session_token=session_token)
        secondary_client = boto3.client('rds', region_name=secondary_region, aws_access_key_id=access_key, aws_secret_access_key=secret_access_key, aws_session_token=session_token)
        
        dr_condition = input("Is the DR condition activated? (yes/no): ")
        if dr_condition.lower() == "yes":
            handle_disaster_recovery(primary_client, secondary_client, primary_cluster_identifier, secondary_cluster_identifier)
        else:
            print("DR condition is not activated. No actions taken.")
    
    elif db_engine.lower() == "mssql":
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
    
    else:
        print("Invalid DB engine. Please enter 'AuroraPostgres' or 'MSSQL'.")

if __name__ == "__main__":
    main()