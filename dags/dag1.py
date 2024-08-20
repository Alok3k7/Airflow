from airflow.decorators import dag
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from datetime import datetime

default_args = {
    'start_date': datetime(2023, 10,28)
}


@dag(
    default_args=default_args,
    schedule_interval='@daily',
    catchup=False

)
def dag1():
    # tasks
    start_task = DummyOperator(
        task_id='start',
    )

    task1 = DummyOperator(
        task_id='task1',
    )

    task2 = DummyOperator(
        task_id='task2',
    )

    trigger_dag2_task = TriggerDagRunOperator(
        task_id='trigger_dag2',
        trigger_dag_id="dag2",
        #execution_date="{{ ds }}",
        wait_for_completion=True,
        #poke_interval=60,
        reset_dag_run=True,
        failed_states=["failed"]
    )

    # dependencies
    start_task >> task1 >> task2 >> trigger_dag2_task


dag = dag1()
