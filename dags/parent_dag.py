from airflow import DAG
from airflow.operators.subdag import SubDagOperator
from airflow.decorators import dag, task
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.dummy import DummyOperator
from groups.child_task import child_dag
from airflow.sensors.date_time import DateTimeSensor
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from datetime import datetime, timedelta
import time
from typing import Dict

customers = {
    "customers_snowflake": {
        "name": "snowflake",
        "path": "/customer/snowflake",
        "priority": 2,
        "pool": "snowflake"
    },
    "customers_tcs": {
        "name": "tcs",
        "path": "/customer/tcs",
        "priority": 1,
        "pool": "tcs"
    },
    "customers_jio": {
        "name": "jio",
        "path": "/customer/jio",
        "priority": 3,
        "pool": "jio"
    }
}

default_args = {
    "start_date": datetime(2023, 10, 20),
    "retries": 0
}


def _choosing_customer_based_on_day(execution_date):
    day = execution_date.day_of_week
    if day == 1:
        return 'data_extraction_customer_snowflake'
    if day == 3:
        return 'data_extraction_customer_tcs'
    if day == 5:
        return 'data_extraction_customer_jio'
    return "stop"


def _on_success_callback(context):
    print(context)


def _on_failure_callback(context):
    print(context)


def _data_extraction_callback_success(context):
    print('SUCCESS CALLBACK')


def _data_extraction_callback_failure(context):
    print('FAILURE CALLBACK')


def _data_extraction_callback_retry(context):
    print('RETRY CALLBACK')


@dag(
    description="Parent DAG for Data Processing",
    default_args=default_args,
    schedule_interval="@daily",
    tags=["branch_python_operator"],
    catchup=False,
    dagrun_timeout=timedelta(minutes=10),
    on_success_callback=_on_success_callback,
    on_failure_callback=_on_failure_callback
)
def parent_dag():
    start = DummyOperator(task_id="start", trigger_rule='dummy', pool='default_pool',
                          execution_timeout=timedelta(minutes=10))

    '''delay = DateTimeSensor(
        task_id='delay',
        target_time="{{ execution_date.add(hours=9) }}",
        poke_interval=60 * 60,
        mode="reschedule",
        timeout=60 * 60 * 10,
        execution_timeout=10,
        soft_fail=True,
        exponential_backoff=True
        )
'''

    '''choosing_customer_based_on_day = BranchPythonOperator(
        task_id='choosing_customer_based_on_day',
        python_callable=_choosing_customer_based_on_day
    )'''

    # stop = DummyOperator(task_id='stop')

    storing = DummyOperator(task_id='storing', trigger_rule='none_failed_or_skipped')

    trigger_cleaning_xcoms = TriggerDagRunOperator(
        task_id='trigger_cleaning_xcoms',
        trigger_dag_id="cleaning_dag",
        execution_date="{{ ds }}",
        wait_for_completion=True,
        poke_interval=60,
        reset_dag_run=True,
        failed_states=["failed"]
    )
    start >> trigger_cleaning_xcoms >> storing
    # choosing_customer_based_on_day >> stop
    for customer, details in customers.items():
        @task.python(task_id=f"data_extraction_{customer}", retries=3, retry_delay=timedelta(minutes=2),
                     retry_exponential_backoff=True,
                     on_success_callback=_data_extraction_callback_success,
                     on_failure_callback=_data_extraction_callback_failure,
                     on_retry_callback=_data_extraction_callback_success,
                     depends_on_past=True, priority_weight=details["priority"],
                     pool_slots=1, do_xcom_push=False, pool=details['pool'], multiple_outputs=True)
        def data_extraction(customer_name, customer_path):
            time.sleep(2)
            raise ValueError("failed")
            return {"customer_name": customer_name, "customer_address": customer_path}

        data_extraction_values = data_extraction(details['name'], details['path'])
        start >> data_extraction_values
        child_dag(data_extraction_values) >> storing


dag = parent_dag()

"""
Branch operator :-
Branch PythonOperator
Branch SqlOperator
Branch datetime operator
Branch day of week operator
"""

'''
trigger_rule = "all_success"
trigger_rule = "all_failed"
trigger_rule = "all_done"
trigger_rule = "one_failed"
trigger_rule = "one_success]"
trigger_rule = "none_failed"
trigger_rule = "none_skipped"
trigger_rule = "none_failed_or_skipped"
trigger_rule="dummy"
'''
