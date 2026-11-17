import ast
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import jsonlines
import sys
import torch
from textwrap import dedent
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

#####################################################
# Please finish all TODOs in this file for MP2;
#####################################################

def save_file(content, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)

CONFTEST = """import signal

import pytest


@pytest.fixture(autouse=True)
def _per_test_timeout():
    # Fail a single generated test that does not terminate (e.g., an infinite loop
    # caused by an invalid input) instead of losing the whole test suite.
    def handler(signum, frame):
        raise TimeoutError("generated test exceeded 10 seconds")
    previous = signal.signal(signal.SIGALRM, handler)
    signal.alarm(10)
    yield
    signal.alarm(0)
    signal.signal(signal.SIGALRM, previous)
"""


def extract_test_code(response):
    # Take the code inside Markdown fences; a fence left open because the response hit the
    # token limit runs to the end of the response.
    blocks = re.findall(r'```(?:python|py)?[ \t]*\n(.*?)(?:```|\Z)', response, re.DOTALL)
    return '\n\n'.join(blocks).strip() if blocks else response.strip()


def split_top_level_chunks(code):
    # Split the code into top-level statements (imports, test functions, ...). Lines that
    # start with a closing bracket continue the previous chunk; decorators join the next one.
    chunks = []
    for line in code.splitlines():
        starts_chunk = line.strip() and not line[0].isspace() and line[0] not in ')]}'
        if starts_chunk and not (chunks and chunks[-1][-1].startswith('@')):
            chunks.append([line])
        elif chunks:
            chunks[-1].append(line)
        else:
            chunks.append([line])
    return chunks


def repair_chunk(lines):
    # Drop the lines that make a chunk unparsable (a statement cut off by the token limit, or a
    # typo such as `assert remove remove_vowels(...)`), keeping the remaining assertions.
    lines = list(lines)
    while lines:
        try:
            tree = ast.parse('\n'.join(lines))
        except SyntaxError as error:
            line_no = error.lineno if error.lineno and error.lineno <= len(lines) else len(lines)
            if line_no <= 1:
                return None
            del lines[line_no - 1]
            continue
        return lines if tree.body else None
    return None


def sanitize_test_code(code, entry, module_name):
    kept = []
    for chunk in split_top_level_chunks(code):
        lines = repair_chunk(chunk)
        if lines is None:
            continue
        node = ast.parse('\n'.join(lines)).body[0]
        # The tests must exercise the supplied implementation, not a copy of it.
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == entry['entry_point']:
            continue
        kept.append('\n'.join(lines))
    # Make the canonical functions (and pytest) available even if the model omits the imports.
    # Future imports must remain the first statements.
    future = [c for c in kept if c.startswith('from __future__')]
    rest = [c for c in kept if not c.startswith('from __future__')]
    header = future + ['import pytest', f'from {module_name} import *']
    return '\n\n'.join(header + rest) + '\n'


def run_pytest(test_file, module_name, test_dir, report_path, junit_path=None, branch=False):
    command = [
        sys.executable, '-m', 'pytest', test_file, '-v', '-p', 'no:cacheprovider',
        '--continue-on-collection-errors',
        f'--cov={module_name}', '--cov-report=term-missing', f'--cov-report=json:{report_path}',
    ]
    if branch:
        command.append('--cov-branch')
    if junit_path is not None:
        command.append(f'--junitxml={junit_path}')
    try:
        completed = subprocess.run(
            command, cwd=test_dir, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding='utf-8',
            errors='replace', timeout=300,
        )
        return completed.stdout, completed.returncode
    except subprocess.TimeoutExpired as error:
        output = error.stdout or b''
        if isinstance(output, bytes):
            output = output.decode('utf-8', errors='replace')
        return output + '\nPytest timed out after 300 seconds.\n', None


def run_tests(entry, response, vanilla):
    mode = 'vanilla' if vanilla else 'crafted'
    mp2_dir = Path(__file__).resolve().parent
    module_name = entry['task_id'].replace('/', '_').lower()
    test_dir = mp2_dir / 'GeneratedTests' / mode / module_name
    test_dir.mkdir(parents=True, exist_ok=True)
    report_path = mp2_dir / 'Coverage' / f"{entry['task_id'].replace('/', '_')}_test_{mode}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    branch_report_path = test_dir / 'branch_coverage.json'
    junit_path = test_dir / 'test_results.xml'
    test_file = f'{module_name}_test.py'

    # Post-process the response into an executable test file (the raw response stays in JSONL).
    test_code = sanitize_test_code(extract_test_code(response), entry, module_name)
    save_file(test_code, test_dir / test_file)
    save_file(entry['prompt'] + entry['canonical_solution'], test_dir / f'{module_name}.py')
    save_file(CONFTEST, test_dir / 'conftest.py')

    # Do not accidentally read a report from an earlier run.
    for path in (report_path, branch_report_path, junit_path):
        path.unlink(missing_ok=True)
    pytest_output, exit_code = run_pytest(test_file, module_name, test_dir, report_path, junit_path)
    save_file(pytest_output, test_dir / 'pytest.log')
    print(f"Pytest for {entry['task_id']} ({mode}):\n{pytest_output}")

    if not report_path.exists():
        # No test could run (e.g., the whole file failed to import): record the coverage of
        # importing the module without executing any generated test.
        print(f'No coverage report produced; measuring coverage without generated tests: {report_path}')
        save_file(f'import {module_name}\n\n\ndef test_no_generated_tests():\n    pass\n',
                  test_dir / 'no_generated_tests_test.py')
        run_pytest('no_generated_tests_test.py', module_name, test_dir, report_path)
    coverage = None
    if report_path.exists():
        coverage = json.loads(report_path.read_text(encoding='utf-8'))['totals']['percent_covered']

    # Supplementary metric: statement + branch coverage of the same generated tests.
    run_pytest(test_file, module_name, test_dir, branch_report_path, branch=True)
    branch_coverage = None
    if branch_report_path.exists():
        branch_coverage = json.loads(branch_report_path.read_text(encoding='utf-8'))['totals']['percent_covered']

    stats = dict(tests_total=0, tests_passed=0, tests_failed=0, tests_errors=0, tests_skipped=0)
    if junit_path.exists():
        for case in ET.parse(junit_path).iter('testcase'):
            stats['tests_total'] += 1
            if case.find('failure') is not None:
                stats['tests_failed'] += 1
            elif case.find('error') is not None:
                stats['tests_errors'] += 1
            elif case.find('skipped') is not None:
                stats['tests_skipped'] += 1
            else:
                stats['tests_passed'] += 1
    return coverage, dict(branch_coverage=branch_coverage, pytest_exit_code=exit_code, **stats)

def prompt_model(dataset, model_name = "deepseek-ai/deepseek-coder-6.7b-instruct", vanilla = True):
    print(f"Working with {model_name} prompt type {vanilla}...")
    
    # TODO: download the model
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    # TODO: load the model with quantization
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )
    model.eval()
    
    results = []
    for entry in dataset:
        program = entry["prompt"] + entry["canonical_solution"]
        if vanilla:
            instruction = dedent("""\
                Generate a pytest test suite for the following code.
                Only output Python test code, without explanations or documentations.
            """).strip()
        else:
            instruction = dedent(f"""\
                Generate a pytest test suite for {entry['entry_point']} with high statement and branch coverage.

                1. Write 8 to 12 separate test_ functions, each with one to three assertions.
                   Every test must use a different input; do not repeat similar cases.
                2. Cover each branch and early return, and loops that run zero, one, and many times.
                3. Include typical inputs and edge cases such as boundaries, empty inputs, single
                   elements, and duplicates. Only use inputs allowed by the docstring.
                4. Before writing an assertion, trace the code exactly as written to compute the
                   expected result; do not guess. Use pytest.approx for floating-point results.

                Only output Python test code, without explanations or documentations.
            """).strip()

        module_name = entry['task_id'].replace('/', '_').lower()
        instruction += (
            f"\n\nImport the function with: from {module_name} import {entry['entry_point']}.\n"
            "Test the supplied implementation; do not redefine it in the test suite.\n"
            f"\nCode under test:\n```python\n{program.strip()}\n```\n"
        )
        prompt = (
            f"{tokenizer.bos_token}You are an AI programming assistant. You are an AI programming assistant, "
            "utilizing the DeepSeek Coder model, developed by DeepSeek Company, and you only answer "
            "questions related to computer science. For politically sensitive questions, security "
            "and privacy issues, and other non-computer science questions, you will refuse to answer.\n\n"
            f"### Instruction:\n{instruction}\n\n### Response:\n"
        )
        
        # TODO: prompt the model and get the response
        inputs = tokenizer(prompt, add_special_tokens=False, return_tensors="pt").to(model.device)
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=2048,
                do_sample=False,
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.eos_token_id,
            )
        response = tokenizer.decode(
            outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True
        )

        # TODO: process the response, generate coverage and save it to results
        coverage, test_stats = run_tests(entry, response, vanilla)

        print(f"Task_ID {entry['task_id']}:\nprompt:\n{prompt}\nresponse:\n{response}\ncoverage:\n{coverage}")
        results.append({
            "task_id": entry["task_id"],
            "prompt": prompt,
            "response": response,
            "coverage": coverage,
            **test_stats,
        })
        
    return results

def read_jsonl(file_path):
    dataset = []
    with jsonlines.open(file_path) as reader:
        for line in reader: 
            dataset.append(line)
    return dataset

def write_jsonl(results, file_path):
    with jsonlines.open(file_path, "w") as f:
        for item in results:
            f.write_all([item])

if __name__ == "__main__":
    """
    This Python script is to run prompt LLMs for code synthesis.
    Usage:
    `python3 task_2.py <input_dataset> <model> <output_file> <if_vanilla>`|& tee prompt.log

    Inputs:
    - <input_dataset>: A `.jsonl` file, which should be your team's dataset containing 20 HumanEval problems.
    - <model>: Specify the model to use. Options are "deepseek-ai/deepseek-coder-6.7b-base" or "deepseek-ai/deepseek-coder-6.7b-instruct".
    - <output_file>: A `.jsonl` file where the results will be saved.
    - <if_vanilla>: Set to 'True' or 'False' to enable vanilla prompt
    
    Outputs:
    - You can check <output_file> for detailed information.
    """
    args = sys.argv[1:]
    input_dataset = args[0]
    model = args[1]
    output_file = args[2]
    if_vanilla = args[3] # True or False
    
    if not input_dataset.endswith(".jsonl"):
        raise ValueError(f"{input_dataset} should be a `.jsonl` file!")
    
    if not output_file.endswith(".jsonl"):
        raise ValueError(f"{output_file} should be a `.jsonl` file!")
    
    vanilla = True if if_vanilla == "True" else False
    
    dataset = read_jsonl(input_dataset)
    results = prompt_model(dataset, model, vanilla)
    write_jsonl(results, output_file)
