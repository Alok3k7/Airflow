from airflow import DAG
from airflow.decorators import dag, task
from airflow.utils.task_group import TaskGroup
from datetime import datetime, timedelta


@task.python
def extraction():
    client_name = "tricera"
    client_address = "/pune/maharashtra"
    return {"client_name": client_name, "client_address": client_address}


@task.python
def processing_for_1(client_name, client_address):
    print(client_name)
    print(client_address)


@task.python
def processing_for_2(client_name, client_address):
    print(client_name)
    print(client_address)


@task.python
def processing_for_3(client_name, client_address):
    print(client_name)
    print(client_address)


@task.python
def alok():
    print("working")


@task.python
def lucky():
    print("working")


@task.python
def aditya():
    print("working")


default_args = {
    "start_date": datetime(2023, 10, 20)
}


@dag(
    description="task group in progress",
    default_args=default_args,
    schedule_interval="@daily",
    dagrun_timeout=timedelta(minutes=20),
    tags=["task_grouping"],
    catchup=False
)
def taskgroup_dag():
    client_work = extraction()

    with TaskGroup(group_id='processing_tasks', add_suffix_on_collision=True) as processing_tasks:
        with TaskGroup(group_id='tester') as tester:
            alok()
            lucky()
            aditya()
    processing_for_1(client_work['client_name'], client_work['client_address']) >> tester
    processing_for_2(client_work['client_name'], client_work['client_address']) >> tester
    processing_for_3(client_work['client_name'], client_work['client_address']) >> tester

    return processing_tasks


dag = taskgroup_dag()
