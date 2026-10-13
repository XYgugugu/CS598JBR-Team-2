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

def run_tests(entry, response, vanilla):
    mode = 'vanilla' if vanilla else 'crafted'
    mp2_dir = Path(__file__).resolve().parent
    module_name = entry['task_id'].replace('/', '_').lower()
    test_dir = mp2_dir / 'GeneratedTests' / mode / module_name
    test_dir.mkdir(parents=True, exist_ok=True)
    report_path = mp2_dir / 'Coverage' / f"{entry['task_id']}_test_{mode}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    junit_path = test_dir / 'test_results.xml'

    # Remove Markdown fences while preserving the original response in JSONL.
    blocks = re.findall(r'```(?:python|py)?\s*\n(.*?)```', response, re.DOTALL)
    test_code = '\n\n'.join(blocks).strip() if blocks else response.strip()
    # Make the canonical functions available even if the model omits imports.
    # Future imports must remain before this added import.
    import_line = 0
    try:
        for node in ast.parse(test_code).body:
            if isinstance(node, ast.ImportFrom) and node.module == '__future__':
                import_line = node.end_lineno
    except SyntaxError:
        pass  # Let pytest record malformed generated code as a collection error.
    lines = test_code.splitlines()
    lines.insert(import_line, f'from {module_name} import *')
    save_file('\n'.join(lines) + '\n', test_dir / f'{module_name}_test.py')
    save_file(entry['prompt'] + entry['canonical_solution'], test_dir / f'{module_name}.py')

    # Do not accidentally read a report from an earlier run.
    report_path.unlink(missing_ok=True)
    junit_path.unlink(missing_ok=True)
    command = [
        sys.executable, '-m', 'pytest', f'{module_name}_test.py', '-v',
        f'--cov={module_name}', '--cov-report=term-missing',
        f'--cov-report=json:{report_path}', f'--junitxml={junit_path}',
    ]
    try:
        completed = subprocess.run(
            command, cwd=test_dir, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding='utf-8',
            errors='replace', timeout=120,
        )
        pytest_output = completed.stdout
        exit_code = completed.returncode
    except subprocess.TimeoutExpired as error:
        pytest_output = error.stdout or b''
        if isinstance(pytest_output, bytes):
            pytest_output = pytest_output.decode('utf-8', errors='replace')
        pytest_output += '\nPytest timed out after 120 seconds.\n'
        exit_code = None
    save_file(pytest_output, test_dir / 'pytest.log')
    print(f"Pytest for {entry['task_id']} ({mode}):\n{pytest_output}")

    coverage = None
    if report_path.exists() and exit_code is not None:
        report = json.loads(report_path.read_text(encoding='utf-8'))
        coverage = report['totals']['percent_covered']
    else:
        print(f'No completed coverage report available: {report_path}')

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
    return coverage, dict(pytest_exit_code=exit_code, **stats)

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
                Generate a pytest test suite for {entry['entry_point']} with high coverage.

                1. Cover each branch and early return, and different loop lengths where possible.
                2. Include typical inputs and valid edge cases, such as boundaries,
                   empty inputs, single elements, and duplicates.
                3. Calculate each expected result from the code exactly as written.
                4. Use separate test_ functions with assertions. Use pytest.approx
                   when comparing approximate floating-point results.

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
