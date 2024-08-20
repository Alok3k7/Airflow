from airflow.models import DAG
from airflow.operators.dummy import DummyOperator
from datetime import datetime
from airflow.models.baseoperator import cross_downstream, chain

default_args = {
    'start_date': datetime(2023, 10, 25)
}

with DAG('dependency_1_0_2_1',
         schedule_interval='@daily',
         default_args=default_args,
         tags=["dependency"],
         catchup=False
         ) as dag:
    task1 = DummyOperator(task_id='task1')
    task2 = DummyOperator(task_id='task2')

    task4 = DummyOperator(task_id='task4')
    task5 = DummyOperator(task_id='task5')
    task6 = DummyOperator(task_id='task6')
    task7 = DummyOperator(task_id='task7')

    # old way to define dependency
    # task2.set_upstream(task1)
    # task3.set_downstream(task4)

    # new way to define dependency
    # task6 >> task5 >> task4
    # [task3,task2]>>task1

    # cross_downstream way to define cross dependency

    cross_downstream([task2, ], [task4, task5])
    chain(task1, task2, task5, task6, task7)
