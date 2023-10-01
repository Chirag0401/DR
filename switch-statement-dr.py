import boto3
import time

def create_session(region, access_key, secret_access_key, session_token):
    """Create AWS session."""
    session = boto3.Session(
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_access_key,
        aws_session_token=session_token,
    )
    return session

def promote_mssql_replica(client, replica_identifier):
    """Promote MSSQL read replica."""
    try:
        client.promote_read_replica(DBInstanceIdentifier=replica_identifier)
        print(f"Promoting read replica {replica_identifier}...")
    except Exception as e:
        print(f"Error promoting read replica: {e}")

def promote_aurora_cluster(client, cluster_identifier):
    """Promote Aurora secondary cluster."""
    try:
        client.promote_db_cluster(DBClusterIdentifier=cluster_identifier)
        print(f"Promoting secondary cluster {cluster_identifier}...")
    except Exception as e:
        print(f"Error promoting secondary cluster: {e}")

def modify_mssql_instance(client, db_identifier):
    """Modify MSSQL instance for Multi-AZ and associate option and parameter groups."""
    try:
        # option_group_name = f"{db_identifier}-option-group"
        # parameter_group_name = default.sqlserver-ee-15.0
        client.modify_db_instance(
            DBInstanceIdentifier=db_identifier,
            MultiAZ=True,
            # OptionGroupName=option_group_name,
            # DBParameterGroupName=parameter_group_name,
            ApplyImmediately=True
        )
        # print(f"Modifying {db_identifier} for Multi-AZ... and aassociating option group {option_group_name} and parameter groups {parameter_group_name} for {db_identifier}...")
        print(f"Creating and associating option and parameter groups for {db_identifier}...")
        time.sleep(60)


        
        # client.create_option_group(
        #     OptionGroupName=option_group_name,
        #     EngineName="sqlserver-ee",
        #     MajorEngineVersion="15.00",
        #     OptionGroupDescription=f"Option group for {db_identifier}"
        # )
        # client.create_db_parameter_group(
        #     DBParameterGroupName=parameter_group_name,
        #     DBParameterGroupFamily="sqlserver-15.00",
        #     Description=f"Parameter group for {db_identifier}"
        # )
        # client.modify_db_instance(
        #     DBInstanceIdentifier=db_identifier,
        #     OptionGroupName=option_group_name,
        #     DBParameterGroupName=parameter_group_name,
        #     ApplyImmediately=True
        # )

    except Exception as e:
        print(f"Error modifying instance and associating groups: {e}")

def modify_aurora_cluster(client, cluster_identifier):
    """Modify Aurora cluster global settings."""
    try:
        client.modify_db_cluster(
            DBClusterIdentifier=cluster_identifier,
            DeletionProtection=False,
            EnableGlobalWriteForwarding=False,
            EnableGlobalReadForwarding=False
        )
        print(f"Modifying cluster {cluster_identifier} global settings...")
    except Exception as e:
        print(f"Error modifying cluster global settings: {e}")

def handle_disaster_recovery(db_engine, primary_client, secondary_client, primary_identifier, secondary_identifier):
    """Handle disaster recovery based on the DB engine."""
    print(f"Primary {db_engine} identifier {primary_identifier} is not available. Initiating disaster recovery...")
    if db_engine == 'mssql':
        promote_mssql_replica(secondary_client, secondary_identifier)
        time.sleep(600)
        modify_mssql_instance(secondary_client, secondary_identifier)
    elif db_engine == 'aurora-postgres':
        promote_aurora_cluster(secondary_client, secondary_identifier)
        time.sleep(600)
        modify_aurora_cluster(secondary_client, secondary_identifier)

def update_route53_record(cluster_name, listener_endpoint):
    client = boto3.client('route53')

    hosted_zone_id = 'Z013331831UCZJOQ6RVBQ'  # Replace with your Route 53 hosted zone ID
    record_name = 'database-primary.mssql.com.patch.bcs.local'  # Replace with the record name you want to update
    ttl = 300  # Replace with the desired TTL value

    response = client.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            'Changes': [
                {
                    'Action': 'UPSERT',
                    'ResourceRecordSet': {
                        'Name': record_name,
                        'Type': 'CNAME',
                        'TTL': ttl,
                        'ResourceRecords': [
                            {
                                'Value': listener_endpoint
                            }
                        ]
                    }
                }
            ]
        }
    )

    print(f"Route 53 record updated successfully. Cluster: {cluster_name}, Listener Endpoint: {listener_endpoint}")

def main():
    db_engine = input("Enter the DB engine (mssql/aurora-postgres): ").lower()
    primary_region = input("Enter the primary region: ")
    secondary_region = input("Enter the secondary region: ")
    primary_identifier = input("Enter the primary identifier: ")
    secondary_identifier = input("Enter the secondary identifier: ")
    
    access_key = ""
    secret_access_key = ""
    session_token = ""


    primary_session = create_session(primary_region, access_key, secret_access_key, session_token)
    secondary_session = create_session(secondary_region, access_key, secret_access_key, session_token)
    
    primary_client = primary_session.client('rds')
    secondary_client = secondary_session.client('rds')

    dr_condition = input("Is the DR condition activated? (yes/no): ").lower()
    if dr_condition == "yes":
        handle_disaster_recovery(db_engine, primary_client, secondary_client, primary_identifier, secondary_identifier)
        
        # Get the listener endpoint of the modified instance
        response = secondary_client.describe_db_instances(DBInstanceIdentifier=secondary_identifier)
        listener_endpoint = response['DBInstances'][0]['Endpoint']['Address']
        
        update_route53_record(secondary_identifier, listener_endpoint)
    else:
        print("DR condition is not activated. No actions taken.")

if __name__ == "__main__":
    main()