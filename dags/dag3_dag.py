from airflow import DAG
from airflow.decorators import task_group
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

import datetime

default_args = {
    "start_date": datetime.datetime(2016, 1, 1),
    "retries": 1,
}

dag = DAG(
    dag_id="dag3",
    schedule_interval="@daily",
    default_args=default_args,
)


def dummy_function():
    pass


@task_group(default_args={"retries": 3})
def group1():
    task1 = PythonOperator(task_id="task1", python_callable=dummy_function)
    task2 = BashOperator(task_id="task2", bash_command="echo Hello World!")


with dag:
    start = PythonOperator(task_id="start", python_callable=dummy_function)
    end = PythonOperator(task_id="end", python_callable=dummy_function)

    group = group1()
    start >> group >> end
