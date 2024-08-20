from airflow import DAG
from airflow import DAG
from airflow.decorators import task, dag
from airflow.operators.subdag import SubDagOperator
from datetime import datetime, timedelta
from subdag.subdag_factory import subdag_factory


@task.python(task_id="extract_partners", do_xcom_push=True, multiple_outputs=True)
def extract():
    partner_name = "netflix"
    partner_path = "/partners/netflix"
    return {"partner_name": partner_name, "partner_path": partner_path}


default_args = {
    "start_date": datetime(2023, 10, 17)
}


@dag(
    description="DAG in charge of processing customer data",
    default_args=default_args,
    schedule_interval="@daily",
    dagrun_timeout=timedelta(minutes=10),
    tags=["data_engineer", "subdag"],
    catchup=False
)
def process_dag():
    process_tasks = SubDagOperator(
        task_id="process_tasks",
        subdag=subdag_factory("process_dag", "process_tasks", default_args=default_args)
    )

    extract() >> process_tasks


dag = process_dag()
