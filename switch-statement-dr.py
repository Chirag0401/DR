import boto3
import time

def create_session(region):
    """Create AWS session."""
    session = boto3.Session(
        region_name=region
    )
    return session

def get_db_tags(client, db_identifier):
    """Get tags for the given RDS instance."""
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']
    region = client.meta.region_name
    response = client.list_tags_for_resource(ResourceName=f'arn:aws:rds:{region}:{account_id}:db:{db_identifier}')
    tags = {tag['Key']: tag['Value'] for tag in response['TagList']}
    return tags

def wait_for_cluster_availability(client, cluster_identifier):
    """Wait for Aurora cluster to become available."""
    waiter = client.get_waiter('db_cluster_available')
    waiter.wait(DBClusterIdentifier=cluster_identifier)
    print(f"Cluster {cluster_identifier} is now available.")

def promote_aurora_cluster(client, cluster_identifier):
    """Promote Aurora secondary cluster."""
    try:
        # Remove the Aurora secondary cluster from the global database
        client.remove_from_global_cluster(
            GlobalClusterIdentifier=cluster_identifier,
            DbClusterIdentifier=cluster_identifier
        )
        print(f"Removed {cluster_identifier} from global database...")

        # Wait for the Aurora cluster to become available
        wait_for_cluster_availability(client, cluster_identifier)

        # Get the writer instance's endpoint
        response = client.describe_db_cluster_members(DBClusterIdentifier=cluster_identifier)
        writer_instance = next((member for member in response['DBClusterMembers'] if member['IsClusterWriter']), None)

        if writer_instance:
            writer_endpoint = writer_instance['Endpoint']
            update_route53_record(writer_endpoint, cluster_identifier)
        else:
            print("No writer instance found for the cluster.")
    except Exception as e:
        print(f"Error promoting secondary cluster: {e}")

def promote_mssql_replica(client, replica_identifier):
    """Promote MSSQL read replica."""
    try:
        client.promote_read_replica(DBInstanceIdentifier=replica_identifier)
        print(f"Promoting read replica {replica_identifier}...")
    except Exception as e:
        print(f"Error promoting read replica: {e}")

def modify_mssql_instance(client, db_identifier):
    """Modify MSSQL instance for Multi-AZ."""
    try:
        client.modify_db_instance(
            DBInstanceIdentifier=db_identifier,
            MultiAZ=True,
            ApplyImmediately=True
        )
        print(f"Creating and associating option and parameter groups for {db_identifier}...")
        time.sleep(60)
    except Exception as e:
        print(f"Error modifying instance and associating groups: {e}")

def update_route53_record(listener_endpoint, cluster_name):
    client = boto3.client('route53')

    tags = get_db_tags(client, cluster_name)
    hosted_zone_id = tags.get('HostedZoneId')
    record_name = tags.get('RecordName')

    response = client.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            'Changes': [
                {
                    'Action': 'UPSERT',
                    'ResourceRecordSet': {
                        'Name': record_name,
                        'Type': 'CNAME',
                        'TTL': 300,
                        'ResourceRecords': [{'Value': listener_endpoint}]
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

    primary_session = create_session(primary_region)
    secondary_session = create_session(secondary_region)

    primary_client = primary_session.client('rds')
    secondary_client = secondary_session.client('rds')

    dr_condition = input("Is the DR condition activated? (yes/no): ").lower()
    if dr_condition == "yes":
        if db_engine == 'mssql':
            promote_mssql_replica(secondary_client, secondary_identifier)
            time.sleep(600)
            modify_mssql_instance(secondary_client, secondary_identifier)
        elif db_engine == 'aurora-postgres':
            promote_aurora_cluster(secondary_client, secondary_identifier)
        else:
            print("Unsupported DB engine.")
    else:
        print("DR condition is not activated. No actions taken.")

if __name__ == "__main__":
    main()
