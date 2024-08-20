import airflow.utils.dates
from airflow.decorators import dag
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.sensors.external_task import ExternalTaskSensor
from datetime import datetime, timedelta

default_args = {
    "owner": "airflow",
    "start_date": datetime(2023, 10, 20)
}


@dag(dag_id="cleaning_dag", default_args=default_args, schedule_interval='@daily', catchup=False)
def cleaning_dag():
    cleaning_xcoms = PostgresOperator(
        task_id="cleaning_xcom",
        sql="sql/CLEANING_XCOM.sql",
        postgres_conn_id="postgres"
    )


dag = cleaning_dag()

""" waiting_for_task = ExternalTaskSensor(
       task_id="waiting_for_task",
       external_dag_id="parent_dag",
       external_task_id="storing",
       failed_states=['failed', 'skipped'],
       allowed_states=['success']
   )"""
