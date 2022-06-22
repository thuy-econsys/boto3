import timeit


def print_execution_time(function_name, runs=1):
    import_module_namespace = f'from __main__ import {function_name}'

    result = timeit.timeit(
        stmt=f'{function_name}()',
        setup=import_module_namespace,
        # globals=globals()  # execution w/in current global namespace, not for imports
        number=runs
    )

    print(f'{function_name} ran {runs} time(s) in {result} seconds')
