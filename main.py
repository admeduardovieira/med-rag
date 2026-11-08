import json
import threading
import random
import datetime as dt
import asyncio
import sqlite3
import llm
import time
from itertools import islice
from pprint import pprint
from types import SimpleNamespace as sn
from tqdm import tqdm

db_path = "db/database_full.db"
filter_case = None

random.seed(42)


class LogOutput:
    def __init__(self, file_path):
        self.log_file = open(file_path, "a")

    def write(self, message):
        self.log_file.write(message)
        self.log_file.flush()

    def flush(self):
        self.log_file.flush()


def logger(file_path):

    output = LogOutput(file_path)

    def log(*args, sep=" ", end="\n", file=output):
        print(*args, sep=sep, end=end, file=file)

    return log


def get_data(source="test", continue_from=None, filter_case=None):
    with open(f"dataset/{source}.json", "r") as f:
        lines = []
        while (line := f.readline()) != "":
            data = json.loads(line)

            if filter_case is not None:
                if data.get("key") == filter_case:
                    lines.append(data)
            else:
                lines.append(data)

        lines = list(reversed(lines))
        random.shuffle(lines)

        index = 0
        if continue_from:
            index = [x.get("key") for x in lines].index(continue_from)

        for line in lines[index:]:
            yield line


def query(sql, timeout=10, log_fn=None):
    conn = None
    timer = None
    try:
        conn = sqlite3.connect(db_path)
        timer = threading.Timer(timeout, lambda: conn.interrupt())
        cursor = conn.cursor()
        timer.start()
        cursor.execute(sql)
        results = cursor.fetchall()
        return results
    except sqlite3.OperationalError as e:
        if log_fn:
            log_fn("Error: ", e)
        return None
    except Exception as e:
        if log_fn:
            log_fn("Error: ", e)
        return None
    finally:
        if timer:
            timer.cancel()
        if conn:
            conn.close()


async def gather_tasks(tasks: dict):
    keys = list(tasks.keys())
    values = await asyncio.gather(*tasks.values())
    return dict(zip(keys, values))


async def run_test_case(case, models, exclude_prompts):
    tasks = {}
    time_a = time.monotonic()
    for model in models:
        task = llm.ai_query(
            message="Please convert this question to SQL: " + case.question_refine,
            model=model,
            max_tokens=len(case.sql) * 2,
            exclude_system_sections=exclude_prompts,
        )
        tasks[model] = task

    results = await gather_tasks(tasks)
    time_b = time.monotonic()

    if (time_b - time_a) < 2.0:
        await asyncio.sleep(1)

    return sn(
        case=case,
        output=results,
    )


def batch_iterator(iterable, batch_size=10):
    batch = []
    count = 0
    for idx, item in enumerate(iterable):
        batch.append((idx, item))
        if len(batch) == batch_size:
            yield count, batch
            count += 1
            batch = []
    if batch:
        yield count, batch


async def main(
    experiment_name,
    batch_size=10,
    batch_limit=-1,
    exclude_prompts={},
    continue_from=None,
    models_filter=None,
    dataset="test",
):

    log = logger(f"output/output_{experiment_name}.log")

    if not continue_from:
        log()
        log("=" * 30)
        log()
        log(
            f"Starting experiment {experiment_name} at {dt.datetime.now().isoformat()}..."
        )
        log()
    models = llm.get_models(models_filter=models_filter)

    # 1000 test cases
    for batch_id, batch in tqdm(
        batch_iterator(
            (sn(**x) for x in get_data(dataset, continue_from)),
            batch_size=batch_size,
        ),
        total=batch_limit if batch_limit > 0 else 1000 // batch_size,
    ):
        if batch_id >= batch_limit:
            break

        tasks = []
        for _, case in batch:
            tasks.append(run_test_case(case, models, exclude_prompts))

        batch_results = await asyncio.gather(*tasks)

        def format_answer(data):
            if data and len(data) > 0:
                return f"{data[0]} ({len(data)} rows)"
            else:
                return data

        for batch_result in batch_results:
            log("*" * 30)
            log()
            log("CASE:", llm.normalize(batch_result.case.key))
            log("QUESTION:", llm.normalize(batch_result.case.question_refine))
            log()
            log("TRUE:", llm.normalize(batch_result.case.sql))
            truth = query(batch_result.case.sql, log_fn=log)
            log()

            for model, response in batch_result.output.items():
                log(f"LLM [{model}]:", response.sql)
                data = query(response.sql, log_fn=log)
                log(f"MODEL:", response.meta.model)
                usage = {
                    "in": response.meta.usage.prompt_tokens,
                    "out": response.meta.usage.completion_tokens,
                }
                log(f"USAGE:", json.dumps(usage))
                log(
                    "ANSWER:",
                    format_answer(data),
                    format_answer(truth),
                )
                log()


# filter_case = "9e98c86301154d7baf44b1654b51c1f0"
batch_size = 5
batch_limit = 200
# exclude_prompts = {"example", "data_preview"}
exclude_prompts = set()
take = 2
continue_from = None
# continue_from = "879e430064f5011919b19ba70a193bc9"

dataset = "test"


models_filter = [
    "deepseek-v3.1",
    "gpt-5",
    "gpt-oss-20b",
    "deepseek-v3",
    "llama3.3-70b",
    "gpt-4o",
    "qwen2p5-vl-32b-instruct",
    "mixtral-8x22b-instruct",
]

exclude_info = "-".join(exclude_prompts) if len(exclude_prompts) else "none"
experiment_name = f"batch_size={batch_size}&n={batch_size * batch_limit}&exclude={exclude_info}&take={take}&dataset={dataset}"

if __name__ == "__main__":
    asyncio.run(
        main(
            experiment_name,
            batch_size,
            batch_limit,
            exclude_prompts,
            continue_from,
            models_filter,
            dataset,
        )
    )
