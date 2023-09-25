import boto3
import subprocess
import os

SECONDARY_REGION = 'eu-central-1'

def create_session(region, access_key, secret_access_key, session_token):
    session = boto3.Session(
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_access_key,
        aws_session_token=session_token,
    )
    return session

def get_user_decision():
    print("Do you want to create a new RDS instance or use an existing one?")
    decision = input("Enter 'new' for a new instance, 'existing' for an existing one: ").strip().lower()
    return decision

def get_database_engine():
    print("Which database engine do you want to use?")
    print("1. MSSQL-server")
    print("2. Aurora Postgres")
    print("3. MySQL")
    choice = input("Enter the number corresponding to the database engine: ")
    if choice == "1":
        return "mssql"
    elif choice == "2":
        return "aurora-postgres"
    elif choice == "3":
        return "mysql"
    else:
        print("Invalid choice. Please try again.")
        return get_database_engine()

def execute_terraform_init(terraform_directory, engine):
    terraform_directory = "/home/ec2-user/DR-RDS"
    os.chdir(terraform_directory)
    if engine == "mssql":
        terraform_directory += "/MSSQL-Server/Cluster"
        subprocess.call(["terraform", "init", "-reconfigure", "-backend-config=bucket=terraform-patching-statefiles", "-backend-config=key=RDS/" + engine + "/Cluster/terraform.tfstate", "-backend-config=region=eu-west-1"], cwd=terraform_directory)
        subprocess.call(["terraform", "apply"], cwd=terraform_directory)
    elif engine == "aurora-postgres":
        terraform_directory += "/Aurora-PostgreSQL/Cluster"
        subprocess.call(["terraform", "init", "-reconfigure", "-backend-config=bucket=terraform-patching-statefiles", "-backend-config=key=RDS/Aurora-Postgresql/Cluster/terraform.tfstate", "-backend-config=region=eu-west-1"], cwd=terraform_directory)
        subprocess.call(["terraform", "apply"], cwd=terraform_directory)
    elif engine == "mysql":
        terraform_directory += "/MySQL/Cluster"
        subprocess.call(["terraform", "init", "-reconfigure", "-backend-config=bucket=terraform-patching-statefiles", "-backend-config=key=RDS/" + engine + "/Cluster/terraform.tfstate", "-backend-config=region=eu-west-1"], cwd=terraform_directory)
        subprocess.call(["terraform", "apply"], cwd=terraform_directory)
    else:
        print("Invalid engine. Please try again.")
        exit(1)

def setup_new_rds(terraform_directory, engine):
    execute_terraform_init(terraform_directory, engine)

def search_rds_instance(client, db_identifier):
    try:
        response = client.describe_db_instances(DBInstanceIdentifier=db_identifier)
        if response.get("DBInstances"):
            return True
        return False
    except client.exceptions.DBInstanceNotFoundFault:
        return False

def use_existing_rds(client):
    db_identifier = input("Please provide the DBIdentifier for the existing RDS instance: ")
    if search_rds_instance(client, db_identifier):
        print(f"RDS instance with DBIdentifier {db_identifier} found.")
    else:
        print(f"No RDS instance with DBIdentifier {db_identifier} found.")
        exit(1)
    return db_identifier

def create_or_verify_replica(client, primary_db_identifier):
    decision = input("Have you already created a read replica for this RDS instance? (yes/no): ").strip().lower()
    if decision == 'no':
        terraform_directory = "/home/ec2-user/DR-RDS"
        if primary_db_identifier.startswith("mssql"):
            terraform_directory += "/MSSQL-Server/Read-Replica"
        elif primary_db_identifier.startswith("primary"):
            terraform_directory += "/Aurora-PostgreSQL/Read-Replica"
        elif primary_db_identifier.startswith("mysql"):
            terraform_directory += "/MySQL/Read-Replica"
        else:
            print("Invalid primary DB identifier. Please try again.")
            exit(1)
        os.chdir(terraform_directory)
        try:
            if primary_db_identifier.startswith("mssql"):
                subprocess.call(["terraform", "init", "-reconfigure", "-backend-config=bucket=terraform-patching-statefiles", "-backend-config=key=RDS/MSSQL-Server/Replica/terraform.tfstate", "-backend-config=region=eu-west-1"], cwd=terraform_directory)
                subprocess.call(["terraform", "apply"], cwd=terraform_directory)
            elif primary_db_identifier.startswith("primary"):
                subprocess.call(["terraform", "init", "-reconfigure", "-backend-config=bucket=terraform-patching-statefiles", "-backend-config=key=RDS/Aurora-Postgresql/Replica/terraform.tfstate", "-backend-config=region=eu-west-1"], cwd=terraform_directory)
                subprocess.call(["terraform", "apply"], cwd=terraform_directory)
            elif primary_db_identifier.startswith("mysql"):
                subprocess.call(["terraform", "init", "-reconfigure", "-backend-config=bucket=terraform-patching-statefiles", "-backend-config=key=RDS/" + primary_db_identifier + "-replica/terraform.tfstate", "-backend-config=region=eu-west-1"], cwd=terraform_directory)
                subprocess.call(["terraform", "apply"], cwd=terraform_directory)
            else:
                print("Invalid primary DB identifier. Please try again.")
                exit(1)
        except Exception as e:
            print(f"Error creating read replica: {e}")
    else:
        replica_name = input("Please provide the DBIdentifier of the existing read replica: ")
        try:
            response = client.describe_db_instances(DBInstanceIdentifier=replica_name)
            if not response.get("DBInstances"):
                print(f"No read replica with DBIdentifier {replica_name} found.")
                exit(1)
        except Exception as e:
            print(f"Error verifying read replica: {e}")
            exit(1)

def main():
    region = "eu-west-1"
    access_key = ""
    secret_access_key = ""
    session_token = ""

    session = create_session(region, access_key, secret_access_key, session_token)
    rds_client = session.client('rds')

    decision = get_user_decision()
    if decision == 'new':
        engine = get_database_engine()
        setup_new_rds("/home/ec2-user/DR-RDS/Cluster", engine)
    elif decision == 'existing':
        db_identifier = use_existing_rds(rds_client)
        create_or_verify_replica(rds_client, db_identifier)
    else:
        print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()