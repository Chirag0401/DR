import boto3
import subprocess
import os
import argparse
import configparser
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

def create_session():
    return boto3.Session(
        region_name="eu-west-1",
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        aws_session_token=os.environ.get('AWS_SESSION_TOKEN'),
    )

def execute_terraform_init(engine, component, config):
    terraform_path = os.path.join(config['PATHS']['TerraformDirectory'], engine, component)
    
    # Check if the terraform path exists
    if not os.path.exists(terraform_path):
        logger.error(f"Terraform path '{terraform_path}' does not exist.")
        return
    
    os.chdir(terraform_path)
    subprocess.call(["terraform", "init", "-reconfigure",
                     f"-backend-config=bucket={config['TERRAFORM']['StatefileBucket']}",
                     f"-backend-config=key=RDS/{engine}/{component}/terraform.tfstate",
                     f"-backend-config=region=eu-west-1"], cwd=terraform_path)
    subprocess.call(["terraform", "apply"], cwd=terraform_path)

def search_rds_instance(client, db_identifier):
    try:
        response = client.describe_db_instances(DBInstanceIdentifier=db_identifier)
        return bool(response.get("DBInstances"))
    except client.exceptions.DBInstanceNotFoundFault:
        return False

def main():
    parser = argparse.ArgumentParser(description="Manage RDS instances with Terraform.")
    parser.add_argument("--config", default="config.ini", help="Path to configuration file.")
    args = parser.parse_args()

    # Read configuration from the file
    config = configparser.ConfigParser()
    config.read(args.config)

    session = create_session()
    rds_client = session.client('rds')

    decision = input("Do you want to create a new RDS instance or use an existing one? [new/existing]: ").strip().lower()

    if decision == 'new':
        engine = input("Which database engine do you want to use? [MSSQL-Server/Aurora-PostgreSQL/other]: ").strip()
        execute_terraform_init(engine, "Cluster", config)
    elif decision == 'existing':
        db_identifier = input("Please provide the DBIdentifier for the existing RDS instance: ").strip()
        if search_rds_instance(rds_client, db_identifier):
            logger.info(f"RDS instance with DBIdentifier {db_identifier} found.")
            engine_mapping = {
                "mssql": "MSSQL-Server",
                "primary": "Aurora-PostgreSQL"
                # Add more mappings if needed
            }
            engine = engine_mapping.get(db_identifier.split('-')[0], 'other')
            execute_terraform_init(engine, "Read-Replica", config)
        else:
            logger.error(f"No RDS instance with DBIdentifier {db_identifier} found.")

if __name__ == "__main__":
    main()
