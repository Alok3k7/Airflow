from airflow.decorators import dag
from airflow.operators.dummy_operator import DummyOperator
from datetime import datetime

default_args = {
    'start_date': datetime(2023, 10,28)
}


@dag(
    default_args=default_args,
    schedule_interval='@daily',
    catchup=False

)
def dag2():
    start_task = DummyOperator(
        task_id='start'
    )
    it_working = DummyOperator(
        task_id='it_working'
    )
    stop_task = DummyOperator(
        task_id="stop"
    )

    start_task >> it_working >> stop_task


dag = dag2()
