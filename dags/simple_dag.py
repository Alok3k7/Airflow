from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.filesystem import FileSensor
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
from airflow.models.baseoperator import chain, cross_downstream

from datetime import datetime, timedelta

default_args = {
    'retry': 5,
    'retry_delay': timedelta(minutes=5),
}


def _downloading_data(ti, **kwargs):
    with open('/tmp/my_file.txt', 'w') as f:
        f.write('my_data')
    ti.xcom_push(key='my key', value=43)


def _checking_data(ti):
    print("check data")


with DAG(dag_id='simple_dag', default_args=default_args, schedule_interval="@daily", start_date=days_ago(3),
         catchup=True) as dag:
    downloading_data = PythonOperator(
        task_id='downloading_data',
        python_callable=_downloading_data
    )

    checking_data = PythonOperator(
        task_id='checking_data',
        python_callable=_checking_data
    )

    waiting_for_data = FileSensor(
        task_id='waiting_for_data',
        fs_conn_id='fs_default',
        filepath='my_file.txt'
    )

    processing_data = BashOperator(
        task_id='processing_data',
        bash_command='exit 0'
    )

    # Set up task dependencies
    #    downloading_data.set_downstream(waiting_for_data)
    #    waiting_for_data.set_downstream(processing_data)

    #    processing_data.set_upstream(waiting_for_data)
    #    waiting_for_data .set_upstream(downloading_data)

    # downloading_data >> waiting_for_data >> processing_data

    # downloading_data >> [waiting_for_data, processing_data]

    # chain(downloading_data, waiting_for_data,processing_data )

    cross_downstream([downloading_data, checking_data], [waiting_for_data, processing_data])