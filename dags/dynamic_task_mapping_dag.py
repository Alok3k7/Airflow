from airflow.decorators import task, dag
from airflow.operators.bash import BashOperator

from datetime import datetime

import random

default_args = {
    'start_date': datetime(2023, 10, 1)
}


@dag(schedule_interval="@daily",
     default_args=default_args,
     catchup=False
     )
def dynamic_task_mapping():
    @task.python
    def get_file():
        return ["file_{nb}" for nb in range(random.randint(3, 5))]

    @task.python
    def download_files(folder: str, file: str):
        return f"ls {folder}/{file};exit 0"

    files = download_files.partial(folder='/usr/local').expand(file=get_file())

    BashOperator.partial(task_id="ls file").expand(bash_command=files)


dag = dynamic_task_mapping()
