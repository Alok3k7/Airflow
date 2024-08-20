"""
BRS - DAG
"""
import json
import math
import random
import uuid
from http.client import HTTPException
from datetime import datetime

import pendulum
import requests

from airflow import DAG
from airflow.decorators import task
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python import BranchPythonOperator #
from airflow.operators.slack_operator import SlackAPIPostOperator
from airflow.models import Variable
from airflow.providers.google.cloud.operators.dataproc import (
    DataprocCreateClusterOperator,
    DataprocSubmitJobOperator,
    DataprocDeleteClusterOperator,
)
from airflow.providers.google.cloud.transfers.gcs_to_gcs import GCSToGCSOperator
from google.protobuf.internal.well_known_types import Duration
from requests.auth import HTTPBasicAuth


# GCS Configs
CLOUD_STORAGE_SOURCE_BUCKET = Variable.get("CLOUD_STORAGE_SOURCE_BUCKET")
CLOUD_STORAGE_ARCHIVE_BUCKET = Variable.get("CLOUD_STORAGE_ARCHIVE_BUCKET")

# GCP Dataproc Configs
CLUSTER_NAME = "brs-airflow-cluster-{{ task_instance.xcom_pull('get_batch_key') }}"
REGION = Variable.get("GOOGLE_REGION")
PROJECT_ID = Variable.get("GOOGLE_PROJECT_ID")
PYSPARK_URI = Variable.get("BRS_PYSPARK_FILE_URI")
CLUSTER_STG_TEMP_BUCKET_NAME = Variable.get("CLUSTER_STG_TEMP_BUCKET_NAME")
CLUSTER_STG_CONFIG_BUCKET_NAME = Variable.get("CLUSTER_STG_CONFIG_BUCKET_NAME")
CLUSTER_INIT_CONFIG_FILE = Variable.get("CLUSTER_INIT_CONFIG_FILE")
CLUSTER_SUBNETWORK_URI = Variable.get("CLUSTER_SUBNETWORK_URI")
POSTGRESQL_SPARK_JAR_FILE_PATH = Variable.get("POSTGRESQL_SPARK_JAR_FILE_PATH")

# atlas credentials
ATLAS_URL = Variable.get("ATLAS_URL")
ATLAS_USER = Variable.get("ATLAS_USER")
ATLAS_PASSWORD = Variable.get("ATLAS_PASSWORD")

CLUSTER_CONFIG = {
    "temp_bucket": CLUSTER_STG_TEMP_BUCKET_NAME,
    "config_bucket": CLUSTER_STG_CONFIG_BUCKET_NAME,
    "software_config": {"image_version": "2.0.47-debian10"},
    "initialization_actions": [
        {
            "executable_file": CLUSTER_INIT_CONFIG_FILE,
        }
    ],
    "gce_cluster_config": {
        "network_uri": "",
        "subnetwork_uri": CLUSTER_SUBNETWORK_URI,
        "internal_ip_only": False,
        "zone_uri": f"{REGION}-a",
        "service_account_scopes": ["https://www.googleapis.com/auth/cloud-platform"],
    },
    "lifecycle_config": {"idle_delete_ttl": Duration.FromJsonString(Duration, "900s")},
    "master_config": {
        "num_instances": 1,
        "machine_type_uri": "n1-standard-2",
        "disk_config": {"boot_disk_type": "pd-standard", "boot_disk_size_gb": 512},
    },
    "worker_config": {
        "num_instances": 2,
        "machine_type_uri": "n1-standard-2",
        "disk_config": {"boot_disk_type": "pd-standard", "boot_disk_size_gb": 512},
    },
}

CLUSTER_METADATA = [("pip_packages", "google-cloud-secret-manager==1.0.2")]

PYSPARK_JOB = {
    "reference": {"project_id": PROJECT_ID},
    "placement": {"cluster_name": CLUSTER_NAME},
    "pyspark_job": {
        "main_python_file_uri": PYSPARK_URI,
        "jar_file_uris": [POSTGRESQL_SPARK_JAR_FILE_PATH],
        "args": [
            "--dataset-file",
            "{{ dag_run.conf['dataset_file_path'] }}",
            "--batch-key",
            "{{ task_instance.xcom_pull('get_batch_key') }}",
            "--google-project-id",
            PROJECT_ID,
        ],
    },
}


with DAG(
    dag_id="BRS",
    description="Process and load BRS data in PostgreSQL",
    schedule_interval=None,
    start_date=pendulum.datetime(2021, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    tags=["TRANSFORMATION-DAG"],
    default_args={
        "owner": "Argus First Inc.",
        "depends_on_past": False,
        "email_on_failure": False,
        "email_on_retry": False,
        "retries": 0,
    },
) as dag:
    """
    Airflow DAG for monitoring and executing ELT jobs for BRS dataset.
    """
    start = DummyOperator(task_id="start")
    stop = DummyOperator(task_id="stop")

    @task(task_id="get_batch_key")
    def get_batch_key():
        """Generate unique batch key"""
        return str(uuid.uuid4().node) + str(random.randint(100, 999))

    get_batch_key = get_batch_key()

    @task(task_id="validate_dag_run_config")
    def validate_dag_run_config(**kwargs):
        """Validate DAG run configs"""
        conf = kwargs["dag_run"].conf
        dataset_file_path = conf.get("dataset_file_path", None)

        if not dataset_file_path:
            raise ValueError(
                "[ERROR] - Invalid dataset_file_path provided in the dag_run config."
            )

        return True

    validate_dag_run_config = validate_dag_run_config()

    create_dataproc_cluster = DataprocCreateClusterOperator(
        task_id="create_dataproc_cluster",
        project_id=PROJECT_ID,
        cluster_config=CLUSTER_CONFIG,
        region=REGION,
        cluster_name=CLUSTER_NAME,
        metadata=CLUSTER_METADATA,
    )

    execute_spark_job_and_load_data_in_postgresql = DataprocSubmitJobOperator(
        task_id="execute_spark_job_and_load_data_in_postgresql",
        job=PYSPARK_JOB,
        region=REGION,
        project_id=PROJECT_ID,
    )

    delete_dataproc_cluster = DataprocDeleteClusterOperator(
        task_id="delete_dataproc_cluster",
        project_id=PROJECT_ID,
        cluster_name=CLUSTER_NAME,
        region=REGION,
    )

    @task(task_id="archive_source_file")
    def archive_source_file(**context):
        conf = context["dag_run"].conf
        dataset_file_path = conf.get("dataset_file_path", "")

        archive_source_file_helper = GCSToGCSOperator(
            task_id="archive_source_file",
            source_bucket=CLOUD_STORAGE_SOURCE_BUCKET,
            source_object=dataset_file_path.replace(
                f"gs://{CLOUD_STORAGE_SOURCE_BUCKET}/", ""
            ),
            destination_bucket=CLOUD_STORAGE_ARCHIVE_BUCKET,
            move_object=True,
        )

        return archive_source_file_helper.execute(context=context)

    archive_source_file = archive_source_file()

    @task(task_id="clean_up_temp_data_on_failed", trigger_rule="all_done")
    def clean_up_temp_data_on_failed(**kwargs):
        """Clean up temp files created by the previous jobs or files those got processed."""
        headers = {"Content-Type": "application/json"}
        auth = HTTPBasicAuth(
            Variable.get("DJANGO_API_USER_SECRET"),
            Variable.get("DJANGO_API_PASSWORD_SECRET"),
        )

        response = requests.delete(
            url=f"{Variable.get('DJANGO_API_HOST')}/api/v1/profile/batch/{kwargs['ti'].xcom_pull('get_batch_key')}/",
            auth=auth,
            headers=headers,
        )
        if response.status_code != 200:
            raise HTTPException(
                {"message": response.text, "status_code": response.status_code}
            )

        return True

    clean_up_temp_data_on_failed = clean_up_temp_data_on_failed()

    def _is_spark_job_executed(**kwargs):
        ti = kwargs["ti"]
        xcom_value = ti.xcom_pull(
            task_ids="execute_spark_job_and_load_data_in_postgresql"
        )

        if not xcom_value:
            return "clean_up_temp_data_on_failed"
        else:
            return "delete_dataproc_cluster"

    is_spark_job_executed = BranchPythonOperator(
        task_id="is_spark_job_executed",
        python_callable=_is_spark_job_executed,
        do_xcom_push=False,
    )

    # Slack integration
    @task(task_id="notify_failed_status_on_slack", trigger_rule="one_failed")
    def notify_failed_status_on_slack(**context):
        failed_alert = SlackAPIPostOperator(
            task_id="notify_failed_status_on_slack",
            token=Variable.get("SLACK_API_KEY"),
            text=f":cold_sweat: *DAG EXECUTION FAILED*"
            f"\n\n*DAG ID:* {str(context['dag'].dag_id)}"
            f"\n*RUN ID:* {str(context['run_id'])}"
            f"\n\n\n_Please keep in mind that the *GCP Dataproc cluster might not be deleted* in order to keep_ "
            f"_Spark job logs for debugging purposes._ "
            f"_Please manually debug the script and delete the Dataproc cluster._"
            f"\n*CLUSTER NAME:* brs-airflow-cluster-{context['ti'].xcom_pull('get_batch_key')}"
            f"\n*CLUSTER REGION:* {REGION}"
            f"\n*PROJECT ID:* {PROJECT_ID}",
            channel="spear-dag-notifications",
            username="Google Cloud Composer - Airflow",
        )
        return failed_alert.execute(context=context)

    notify_failed_status_on_slack = notify_failed_status_on_slack()

    @task(task_id="notify_success_status_on_slack", trigger_rule="all_success")
    def notify_success_status_on_slack(**context):
        success_alert = SlackAPIPostOperator(
            task_id="notify_success_status_on_slack",
            token=Variable.get("SLACK_API_KEY"),
            text=f":star-struck: *DAG EXECUTION SUCCESSFUL*"
            f"\n\n*DAG ID:* {str(context['dag'].dag_id)}"
            f"\n*RUN ID:* {str(context['run_id'])}",
            channel="spear-dag-notifications",
            username="Google Cloud Composer - Airflow",
        )
        return success_alert.execute(context=context)

    notify_success_status_on_slack = notify_success_status_on_slack()

    # Task Execution Sequence - Prod
    start >> validate_dag_run_config
    validate_dag_run_config >> get_batch_key
    get_batch_key >> create_dataproc_cluster
    create_dataproc_cluster >> execute_spark_job_and_load_data_in_postgresql
    execute_spark_job_and_load_data_in_postgresql >> is_spark_job_executed
    is_spark_job_executed >> delete_dataproc_cluster
    delete_dataproc_cluster >> archive_source_file
    archive_source_file >> notify_success_status_on_slack

    is_spark_job_executed >> clean_up_temp_data_on_failed
    clean_up_temp_data_on_failed >> notify_failed_status_on_slack

    validate_dag_run_config >> notify_failed_status_on_slack
    get_batch_key >> notify_failed_status_on_slack
    create_dataproc_cluster >> notify_failed_status_on_slack
    clean_up_temp_data_on_failed >> notify_failed_status_on_slack
    delete_dataproc_cluster >> notify_failed_status_on_slack
    archive_source_file >> notify_failed_status_on_slack

    notify_success_status_on_slack >> stop
    notify_failed_status_on_slack >> stop