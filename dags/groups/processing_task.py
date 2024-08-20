from airflow.decorators import task, task_group
from airflow.utils.task_group import TaskGroup


@task.python
def process_data_1(customer_name, customer_address):
    print(customer_name)
    print(customer_address)


@task.python
def process_data_2(customer_name, customer_address):
    print(customer_name)
    print(customer_address)


@task.python
def process_data_3(customer_name, customer_address):
    print(customer_name)
    print(customer_address)


@task.python
def check_1():
    print("checking")


@task.python
def check_2():
    print("checking")


@task.python
def check_3():
    print("checking")


def processing_task(customer_data):
    with TaskGroup(group_id='processing_tasks') as processing_tasks:
        with TaskGroup(group_id='test_tasks') as test_task:
            check_1()
            check_2()
            check_3()
        process_data_1(customer_data['customer_name'], customer_data['customer_address']) >> test_task
        process_data_2(customer_data['customer_name'], customer_data['customer_address']) >> test_task
        process_data_3(customer_data['customer_name'], customer_data['customer_address']) >> test_task
    return processing_tasks


