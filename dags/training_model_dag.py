# all the Import
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.bash import BashOperator
from random import randint
from datetime import datetime, timedelta


# Define a function
def _choose_best_model(ti):
    accuracies = ti.xcom_pull(task_ids=[
        "training_model_A",
        "training_model_B",
        "training_model_C"
    ])
    best_accuracy = max(accuracies)
    if best_accuracy > 8:
        return "accurate"
    return "inaccurate"


def training_model():
    return randint(1, 10)


# DAG

with DAG("training_model_dag", start_date=datetime(2023, 10, 12),
         schedule_interval="@daily", catchup=False, max_active_runs=2, tags=["data_engineer"],
         dagrun_timeout=timedelta(minutes=10)) as dag:
    # tasks within the DAG
    training_model_A = PythonOperator(
        task_id="training_model_A",
        python_callable=training_model
    )

    training_model_B = PythonOperator(
        task_id="training_model_B",
        python_callable=training_model
    )

    training_model_C = PythonOperator(
        task_id="training_model_C",
        python_callable=training_model
    )

    choose_best_model = BranchPythonOperator(
        task_id="choose_best_model",
        python_callable=_choose_best_model
    )

    accurate = BashOperator(
        task_id="accurate",
        bash_command="echo 'accurate'"
    )

    inaccurate = BashOperator(
        task_id="inaccurate",
        bash_command="echo 'inaccurate'"
    )

    #  task dependencies
    [training_model_C, training_model_B, training_model_A, ] >> choose_best_model >> [inaccurate, accurate]