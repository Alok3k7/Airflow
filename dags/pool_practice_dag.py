from airflow.decorators import dag, task
from airflow.utils.dates import datetime

default_args = {
    'start_date': datetime(2023, 10, 1),
    'pool': 'team_a'

}


@dag(
    default_args=default_args,
    schedule_interval="@daily"
)
def pool_practice():
    @task.python
    def start():
        print('start')

    @task.python
    def process():
        print('process')

    @task.python
    def stop():
        print(stop)

    start = start()
    process = process()
    stop = stop()

    start >> process >> stop


dag = pool_practice()
