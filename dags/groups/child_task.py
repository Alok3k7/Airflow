from airflow.decorators import task
from airflow.utils.task_group import TaskGroup


@task.python
def process_data_1(customer_name, customer_path):
    print(customer_name)
    print(customer_path)


@task.python
def process_data_2(customer_name, customer_path):
    print(customer_name)
    print(customer_path)


@task.python
def process_data_3(customer_name, customer_path):
    print(customer_name)
    print(customer_path)


def child_dag(customer_data):
    with TaskGroup("data_processing_tasks",add_suffix_on_collision=True) as processing_tasks:
        process_data_1(customer_data["customer_name"], customer_data["customer_path"])
        process_data_2(customer_data["customer_name"], customer_data["customer_path"])
        process_data_3(customer_data["customer_name"], customer_data["customer_path"])
    return processing_tasks
