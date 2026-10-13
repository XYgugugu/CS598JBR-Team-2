import ast
import random
import re
from pathlib import Path

import jsonlines
import sys
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

#####################################################
# Please finish all TODOs in this file for MP2;
#####################################################

def save_file(content, file_path):
    with open(file_path, 'w') as file:
        file.write(content)

def select_test(entry, rng):
    # These tests wrap candidate() or generate inputs inside a loop.
    if entry['task_id'] == 'HumanEval/33':
        return dict(
            call='sort_third([5, 6, 3, 4, 8, 9, 2])',
            assertion='assert tuple(candidate([5, 6, 3, 4, 8, 9, 2])) == tuple([2, 6, 3, 4, 8, 9, 5])',
            expected_output=[2, 6, 3, 4, 8, 9, 5],
        )
    if entry['task_id'] == 'HumanEval/32':
        # First input from its random.Random(42) test loop: -10 - 2*x = 0.
        return dict(
            call='find_zero([-10, -2])',
            assertion='assert abs(-10 - 2 * candidate([-10, -2])) < 1e-4',
            expected_output=-5.0, abs_tol=5e-5,
        )
    cases = []
    for node in ast.walk(ast.parse(entry['test'])):
        if not isinstance(node, ast.Assert):
            continue
        test = node.test
        if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq):
            call, expected = test.left, test.comparators[0]
        elif isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            call, expected = test.operand, ast.Constant(False)
        else:
            call, expected = test, ast.Constant(True)
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == 'candidate':
            cases.append(dict(
                call=ast.unparse(call).replace('candidate(', entry['entry_point'] + '(', 1),
                assertion=ast.unparse(node), expected_output=ast.literal_eval(expected),
            ))
    return rng.choice(cases) if cases else None


def check_response(response, case):
    outputs = re.findall(r"\[Output\](.*?)\[/Output\]", response, re.DOTALL)
    if not outputs:
        return False
    prediction = outputs[-1].rsplit('[Output]', 1)[-1].strip()
    if isinstance(case['expected_output'], str) and prediction == case['expected_output']:
        return True
    try:
        prediction = ast.literal_eval(prediction)
        if 'abs_tol' in case:
            return type(prediction) in (int, float) and abs(prediction - case['expected_output']) < case['abs_tol']
        return prediction == case['expected_output']
    except (ValueError, SyntaxError):
        return False

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
    seed = 120462750136561247505675876249279604055
    rng = random.Random(seed)
    examples = {} if vanilla else {
        entry['task_id']: entry['examples']
        for entry in read_jsonl(Path(__file__).with_name('task_1_examples.jsonl'))
    }
    print(f"Test selection seed: {seed}; greedy decoding; max_new_tokens=2048")
    
    results = []
    for entry in dataset:
        # TODO: create prompt for the model
        # Tip : Use can use any data from the dataset to create 
        #       the prompt including prompt, canonical_solution, test, etc.
        case = select_test(entry, rng)
        if case is None:
            print(f"Skipping {entry['task_id']}: no simple assertion found.")
            continue
        # Remove docstrings so the selected test's answer is not in the prompt.
        program = ast.parse(entry['prompt'] + entry['canonical_solution'])
        for node in ast.walk(program):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
                first = node.body[0]
                if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                    node.body.pop(0)
        inputs = case['call'].split('(', 1)[1][:-1]
        instruction = (
            f"If the inputs are {inputs}, what will the following code return?\n"
            "The return value prediction must be enclosed between [Output] and [/Output] tags. "
            "For example : [Output]prediction[/Output].\n"
        )
        instruction += '\n' + ast.unparse(program)
        if not vanilla:
            instruction = (
                "Use the following Python code exactly as written to predict return values. "
                "Do not fix or rewrite the code. Output the Python value between [Output] and [/Output] tags.\n\n"
                + ast.unparse(program) + '\n\n'
            )
            for example in examples[entry['task_id']]:
                instruction += (
                    f"Evaluate {example['call']}.\n\n### Response:\n"
                    f"{example['explanation']}\n"
                    f"[Output]{example['expected_output']!r}[/Output]\n<|EOT|>\n### Instruction:\n"
                )
            instruction += (
                f"{ast.unparse(program)}\n\nEvaluate {case['call']}. "
                "Return the value between [Output] and [/Output] tags."
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
        response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)

        # TODO: process the response and save it to results
        verdict = check_response(response, case)

        print(f"Task_ID {entry['task_id']}:\nprompt:\n{prompt}\nresponse:\n{response}\nis_correct:\n{verdict}")
        results.append({
            "task_id": entry["task_id"],
            "prompt": prompt,
            "response": response,
            "is_correct": verdict,
            **case
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
    `python3 Task_1.py <input_dataset> <model> <output_file> <if_vanilla>`|& tee prompt.log

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
