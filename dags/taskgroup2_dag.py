from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.decorators import task, dag, task_group
from airflow.utils.task_group import TaskGroup
from datetime import datetime, timedelta

from groups.processing_task import processing_task


@task.python(task_id="data_extraction", do_xcom_push=False, multiple_outputs=True)
def data_extraction():
    customer_name = "ALOK"
    customer_address = "/thane/maharashtra"
    return {"customer_name": customer_name, "customer_address": customer_address}


default_args = {
    "start_date": datetime(2023, 10, 20)
}


@dag(
    description="Task Group Example",
    default_args=default_args,
    dagrun_timeout=timedelta(minutes=20),
    tags=["task_grouping"],
    catchup=False,
    max_active_tasks=1
)
def taskgroup2_dag():
    customer_data = data_extraction()

    processing_task(customer_data)


dag = taskgroup2_dag()
