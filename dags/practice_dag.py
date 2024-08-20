from airflow.decorators import dag, task
from airflow.utils.dates import datetime

default_args = {
    "start_date": datetime(2023, 10, 20),
}


@dag(default_args=default_args)
def practice_dag():
    @task.python
    def start_task():
        print("Start Task")

    @task.python
    def python_task():
        print("This is my Python function")

    @task.python
    def end_task():
        print("End Task")

    start = start_task()
    python = python_task()
    end = end_task()

    start >> python >> end


# Instantiate the DAG
my_dag = practice_dag()
