import boto3
import time

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

if __name__ == "__main__":
    main()