import re
import subprocess
import tempfile
from pathlib import Path

import jsonlines
import sys
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

#####################################################
# Please finish all TODOs in this file for MP3/task_1;
#####################################################

SYSTEM_PROMPT = (
    "You are an AI programming assistant utilizing the DeepSeek Coder model, developed by DeepSeek Company, "
    "and you only answer questions related to computer science. For politically sensitive questions, security "
    "and privacy issues, and other non-computer science questions, you will refuse to answer."
)

CRAFTED_INSTRUCTION = """\
Translate the following Python code into Java 11 so that it behaves identically on every input.

Follow these rules:
1. Complete the Java skeleton below. Keep `class Solution`, the method names, the parameter types and the return types exactly as written, because a test harness calls them directly.
2. Keep every helper method that the skeleton already contains.
3. Follow the Python code statement by statement. Take care where Python and Java differ, such as integer division and modulo, string slicing, list copying, sorting, and character checks.
4. Use only the Java standard library and include every import you use.
5. Output the complete Java code (imports and the whole `class Solution`) between [Java Start] and [Java End], with no explanation.

Python code:
```python
{python}```

Java skeleton:
```java
{skeleton}```"""

EXAMPLE_PYTHON = (
    'from typing import List\n\n\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n'
    '    """ Check if in given list of numbers, are any two numbers closer to each other than\n'
    '    given threshold.\n    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)\n    False\n'
    '    >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)\n    True\n    """\n'
    '    for idx, elem in enumerate(numbers):\n        for idx2, elem2 in enumerate(numbers):\n'
    '            if idx != idx2:\n                distance = abs(elem - elem2)\n'
    '                if distance < threshold:\n                    return True\n\n    return False\n'
)
EXAMPLE_DECLARATION = (
    'import java.util.*;\nimport java.lang.*;\n\nclass Solution {\n'
    '    public boolean hasCloseElements(List<Double> numbers, double threshold) {\n'
)
EXAMPLE_JAVA = (
    'import java.util.*;\nimport java.lang.*;\n\nclass Solution {\n'
    '    public boolean hasCloseElements(List<Double> numbers, double threshold) {\n'
    '        for (int i = 0; i < numbers.size(); i++) {\n'
    '            for (int j = 0; j < numbers.size(); j++) {\n'
    '                if (i != j) {\n'
    '                    double distance = Math.abs(numbers.get(i) - numbers.get(j));\n'
    '                    if (distance < threshold) {\n'
    '                        return true;\n'
    '                    }\n'
    '                }\n'
    '            }\n'
    '        }\n'
    '        return false;\n'
    '    }\n'
    '}\n'
)

SLICE_EXAMPLE_PYTHON = (
    '\n\ndef reverse_third(l: list):\n'
    '    """This function takes a list l and returns a list l\' such that\n'
    '    l\' is identical to l in the indices that are not divisible by three, while its values at the indices\n'
    '    that are divisible by three are the values at those indices of l in reverse order.\n'
    '    >>> reverse_third([1, 2, 3, 4, 5, 6, 7])\n    [7, 2, 3, 4, 5, 6, 1]\n'
    '    >>> reverse_third([3, 1, 4, 1, 5, 9, 2, 6])\n    [2, 1, 4, 1, 5, 9, 3, 6]\n    """\n'
    '    l = list(l)\n    l[::3] = l[::3][::-1]\n    return l\n'
)
SLICE_EXAMPLE_DECLARATION = (
    'import java.util.*;\nimport java.lang.*;\n\nclass Solution {\n'
    '    public List<Integer> reverseThird(List<Integer> l) {\n'
)
SLICE_EXAMPLE_JAVA = (
    'import java.util.*;\nimport java.lang.*;\n\nclass Solution {\n'
    '    public List<Integer> reverseThird(List<Integer> l) {\n'
    '        // l = list(l) makes a copy.\n'
    '        List<Integer> result = new ArrayList<>(l);\n'
    '        // l[::3] starts at index 0 and takes every third element: indices 0, 3, 6, ...\n'
    '        List<Integer> thirds = new ArrayList<>();\n'
    '        for (int i = 0; i < result.size(); i += 3) {\n'
    '            thirds.add(result.get(i));\n'
    '        }\n'
    '        Collections.reverse(thirds);\n'
    '        // Assigning to l[::3] writes the values back to indices 0, 3, 6, ...\n'
    '        for (int i = 0; i < result.size(); i += 3) {\n'
    '            result.set(i, thirds.get(i / 3));\n'
    '        }\n'
    '        return result;\n'
    '    }\n'
    '}\n'
)

EXAMPLES = [
    (EXAMPLE_PYTHON, EXAMPLE_DECLARATION, EXAMPLE_JAVA),
    (SLICE_EXAMPLE_PYTHON, SLICE_EXAMPLE_DECLARATION, SLICE_EXAMPLE_JAVA),
]

def save_file(content, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)

def java_skeleton(declaration):
    return declaration.rstrip() + '\n        // Translate the Python body here.\n    }\n}\n'

def create_prompt(tokenizer, entry, java_entry, vanilla):
    if vanilla:
        instruction = (
            "Can you translate the following Python code into Java?\n"
            "The new Java code must be enclosed between [Java Start] and [Java End]\n\n"
            f"{entry['declaration']}{entry['canonical_solution']}"
        )
    else:
        examples = ''.join(
            CRAFTED_INSTRUCTION.format(python=python, skeleton=java_skeleton(declaration))
            + f"\n\n### Response:\n[Java Start]\n{java}[Java End]\n<|EOT|>\n### Instruction:\n"
            for python, declaration, java in EXAMPLES)
        instruction = (
            examples
            + CRAFTED_INSTRUCTION.format(
                python=entry['prompt'] + entry['canonical_solution'],
                skeleton=java_skeleton(java_entry['declaration']))
        )
    return (
        f"{tokenizer.bos_token}{SYSTEM_PROMPT}\n\n"
        f"### Instruction:\n{instruction}\n\n### Response:\n"
    )

def extract_java(response):
    tagged = re.findall(r'\[Java Start\](.*?)(?:\[Java End\]|$)', response, re.DOTALL | re.IGNORECASE)
    code = max(tagged, key=len) if tagged else response
    fenced = re.findall(r'```[ \t]*(?:java)?[ \t]*\n(.*?)```', code, re.DOTALL)
    if fenced:
        return '\n'.join(fenced).strip()
    return re.sub(r'^[ \t]*```.*$', '', code, flags=re.MULTILINE).strip()

def top_level_types(code):
    types, depth, i = [], 0, 0
    header = re.compile(r'((?:(?:public|private|protected|final|abstract|static)\s+)*)'
                        r'(?:class|interface|enum|record)\s+(\w+)')
    start = name = None
    while i < len(code):
        if code.startswith('//', i):
            i = code.find('\n', i) if '\n' in code[i:] else len(code)
            continue
        if code.startswith('/*', i):
            end = code.find('*/', i + 2)
            i = len(code) if end == -1 else end + 2
            continue
        char = code[i]
        if char in '"\'':
            quote = '"""' if code.startswith('"""', i) else char
            i += len(quote)
            while i < len(code) and not code.startswith(quote, i):
                i += 2 if code[i] == '\\' else 1
            i += len(quote)
            continue
        if depth == 0 and start is None:
            match = header.match(code, i)
            if match and (i == 0 or not (code[i - 1].isalnum() or code[i - 1] == '_')):
                start, name = i, match.group(2)
                i = match.end()
                continue
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0 and start is not None:
                types.append((start, i + 1, name))
                start = None
        i += 1
    if start is not None:
        types.append((start, len(code), name))
    return types

def build_program(response, java_entry):
    code = extract_java(response)
    code = re.sub(r'^\s*package\s+[\w.]+\s*;', '', code, flags=re.MULTILINE)
    imports = re.findall(r'^\s*(import\s+(?:static\s+)?[\w.]+(?:\.\*)?\s*;)', java_entry['declaration'], re.MULTILINE)
    imports += re.findall(r'^\s*(import\s+(?:static\s+)?[\w.]+(?:\.\*)?\s*;)', code, re.MULTILINE)
    code = re.sub(r'^\s*import\s+(?:static\s+)?[\w.]+(?:\.\*)?\s*;[ \t]*\n?', '', code, flags=re.MULTILINE).strip()

    methods = re.findall(r'public\s+[\w<>\[\],.? ]+?\s+(\w+)\s*\(', java_entry['declaration'])
    target = methods[-1]
    types = top_level_types(code)
    if not types:
        code = f"class Solution {{\n{code}\n}}"
    else:
        names = [name for _, _, name in types]
        if 'Solution' in names:
            chosen = 'Solution'
        else:
            with_target = [name for start, end, name in types if re.search(rf'\b{target}\s*\(', code[start:end])]
            chosen = with_target[0] if with_target else names[0]
        for start, end, name in reversed(types):
            if name == 'Main' and name != chosen:
                code = code[:start] + code[end:]
        if chosen != 'Solution':
            code = re.sub(rf'\b{chosen}\b', 'Solution', code)
        code = re.sub(r'^([ \t]*)public\s+((?:(?:final|abstract|static)\s+)*(?:class|interface|enum|record)\s)',
                      r'\1\2', code, flags=re.MULTILINE)
    imports = list(dict.fromkeys(re.sub(r'\s+', ' ', imp) for imp in imports))
    return '\n'.join(imports) + f"\n\n{code}\n\n{java_entry['test']}\n"

def run_java(program, timeout=30):
    with tempfile.TemporaryDirectory() as tmp_dir:
        save_file(program, Path(tmp_dir) / 'Main.java')
        try:
            compiled = subprocess.run(
                ['javac', '-encoding', 'UTF-8', 'Main.java'], cwd=tmp_dir,
                capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return 'compilation error', 'javac timed out after 120 seconds.'
        if compiled.returncode != 0:
            return 'compilation error', compiled.stdout + compiled.stderr
        try:
            executed = subprocess.run(
                ['java', '-ea', '-cp', tmp_dir, 'Main'], cwd=tmp_dir,
                capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return 'timeout', f'Execution timed out after {timeout} seconds.'
        output = executed.stdout + executed.stderr
        if executed.returncode == 0:
            return 'passed', output
        return ('test failure' if 'java.lang.AssertionError' in output else 'runtime error'), output

def prompt_model(dataset, model_name = "deepseek-ai/deepseek-coder-6.7b-instruct", vanilla = True, java_dataset = None):
    print(f"Working with {model_name} prompt type {vanilla}...")
    java_entries = {entry['task_id']: entry for entry in java_dataset}

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
    print("Greedy decoding; max_new_tokens=2048")

    results = []
    for entry in dataset:
        # TODO: create prompt for the model
        # Tip : Use can use any data from the dataset to create 
        #       the prompt including prompt, canonical_solution, test, etc.
        java_entry = java_entries[entry['task_id']]
        prompt = create_prompt(tokenizer, entry, java_entry, vanilla)

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
        program = build_program(response, java_entry)
        result, output = run_java(program)
        verdict = result == 'passed'

        print(f"Task_ID {entry['task_id']}:\nprompt:\n{prompt}\nresponse:\n{response}\n"
              f"java program:\n{program}\nresult: {result}\n{output}\nis_correct:\n{verdict}")
        results.append({
            "task_id": entry["task_id"],
            "prompt": prompt,
            "response": response,
            "is_correct": verdict,
            "result": result,
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
    This Python script is to run prompt LLMs for code translation.
    Usage:
    `python3 task_1.py <input_dataset> <model> <output_file> <if_vanilla>`|& tee prompt.log

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
    java_dataset = read_jsonl(input_dataset.replace("humanevalx_python", "humanevalx_java"))
    results = prompt_model(dataset, model, vanilla, java_dataset)
    write_jsonl(results, output_file)
