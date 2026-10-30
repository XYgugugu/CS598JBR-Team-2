import re

import jsonlines
import sys
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

#####################################################
# Please finish all TODOs in this file for MP3/task_2;
#####################################################

SYSTEM_PROMPT = (
    "You are an AI programming assistant. You are an AI programming assistant utilizing the DeepSeek Coder "
    "model, developed by DeepSeek Company, and you only answer questions related to computer science. For "
    "politically sensitive questions, security and privacy issues, and other non-computer science questions, "
    "you will refuse to answer."
)

VANILLA_INSTRUCTION = """\
{code}

Is the above code buggy or correct? Please explain your step by step reasoning. The prediction should be enclosed within <start> and <end> tags. For example: <start>Buggy<end>"""

REFERENCE_INSTRUCTION = """\
Write a Python implementation of the following function according to its docstring.
Output only the complete function in a single Python code block.

```python
{prompt}```"""

CRAFTED_INSTRUCTION = """\
Review the following Python function for bugs. Its docstring is the specification, and the test function below contains assertions that every correct implementation passes.

Implementation under review:
```python
{code}```

Reference implementation written from the docstring alone (it may also contain mistakes):
```python
{reference}
```

Test cases:
```python
{tests}
```

Decide whether the implementation under review is buggy or correct by following these steps:
1. Specification: state what the function must return according to the docstring.
2. Differences: list every place where the implementation under review differs from the reference implementation, such as conditions, comparison operators, arithmetic, constants, indices and loop bounds, string methods, and missing or extra steps. For each difference, say which version follows the specification.
3. Test check: pick an assertion whose input is affected by a difference you found (or any assertion if there is none), trace the implementation under review on it line by line, and compare the returned value with the expected value.
4. Verdict: the code is buggy if a difference shows that it violates the specification or the traced value differs from the expected value; otherwise it is correct.

End your answer with the verdict enclosed within <start> and <end> tags, either <start>Buggy<end> or <start>Correct<end>."""

# Two worked examples (HumanEval/0 and HumanEval/13, which are not in our dataset): one buggy and one correct.
EXAMPLES = [
    dict(
        code='from typing import List\n\n\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n'
             '    """ Check if in given list of numbers, are any two numbers closer to each other than\n'
             '    given threshold.\n    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)\n    False\n'
             '    >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)\n    True\n    """\n'
             '    for idx, elem in enumerate(numbers):\n        for idx2, elem2 in enumerate(numbers):\n'
             '            if idx != idx2:\n                distance = elem - elem2\n'
             '                if distance < threshold:\n                    return True\n\n    return False\n',
        reference='def has_close_elements(numbers: List[float], threshold: float) -> bool:\n'
                  '    for i in range(len(numbers)):\n        for j in range(i + 1, len(numbers)):\n'
                  '            if abs(numbers[i] - numbers[j]) < threshold:\n                return True\n'
                  '    return False',
        tests='def check(has_close_elements):\n'
              '    assert has_close_elements([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.3) == True\n'
              '    assert has_close_elements([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.05) == False\n'
              '    assert has_close_elements([1.1, 2.2, 3.1, 4.1, 5.1], 0.5) == False\n\n'
              'check(has_close_elements)',
        answer='1. Specification: return True if two different elements of the list are closer than the threshold, '
               'that is, their absolute difference is less than the threshold; otherwise return False.\n\n'
               '2. Differences:\n'
               '- The implementation under review loops over all ordered pairs and skips idx == idx2, while the '
               'reference loops over pairs with j > i. Both compare every pair of different elements, so both follow '
               'the specification.\n'
               '- The implementation under review computes `distance = elem - elem2`, while the reference uses '
               '`abs(numbers[i] - numbers[j])`. The specification is about the distance between two numbers, which '
               'is the absolute difference, so the reference is right and the implementation under review is wrong: '
               'a negative difference is always below a positive threshold.\n\n'
               '3. Test check: `has_close_elements([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.05)` should be False. For '
               'elem=1.0 and elem2=2.0, the implementation computes distance = -1.0, which is less than 0.05, so it '
               'returns True. The values differ.\n\n'
               '4. Verdict: the signed difference violates the specification, and the traced value differs from the '
               'expected value.\n\n<start>Buggy<end>',
    ),
    dict(
        code='\n\ndef greatest_common_divisor(a: int, b: int) -> int:\n'
             '    """ Return a greatest common divisor of two integers a and b\n'
             '    >>> greatest_common_divisor(3, 5)\n    1\n    >>> greatest_common_divisor(25, 15)\n    5\n    """\n'
             '    while b:\n        a, b = b, a % b\n    return a\n',
        reference='def greatest_common_divisor(a: int, b: int) -> int:\n'
                  '    if b == 0:\n        return a\n    return greatest_common_divisor(b, a % b)',
        tests='def check(greatest_common_divisor):\n'
              '    assert greatest_common_divisor(3, 7) == 1\n'
              '    assert greatest_common_divisor(10, 15) == 5\n'
              '    assert greatest_common_divisor(49, 14) == 7\n\n'
              'check(greatest_common_divisor)',
        answer='1. Specification: return the greatest common divisor of a and b.\n\n'
               '2. Differences:\n'
               '- The implementation under review uses a loop, while the reference uses recursion. Both apply the '
               'Euclidean step (a, b) -> (b, a % b) until b is 0 and then return a, so both follow the '
               'specification.\n\n'
               '3. Test check: `greatest_common_divisor(49, 14)` should be 7. (49, 14) -> (14, 7) -> (7, 0), so the '
               'implementation returns 7. The values agree.\n\n'
               '4. Verdict: no difference violates the specification, and the traced value equals the expected '
               'value.\n\n<start>Correct<end>',
    ),
]

def save_file(content, file_path):
    with open(file_path, 'w') as file:
        file.write(content)

def wrap_prompt(tokenizer, instruction):
    return (
        f"{tokenizer.bos_token}{SYSTEM_PROMPT}\n\n"
        f"### Instruction:\n{instruction}\n\n### Response:\n"
    )

def generate(model, tokenizer, prompt, max_new_tokens):
    inputs = tokenizer(prompt, add_special_tokens=False, return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.eos_token_id,
        )
    return tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)

def extract_code(response):
    blocks = re.findall(r'```(?:python|py)?[ \t]*\n(.*?)(?:```|\Z)', response, re.DOTALL)
    return (blocks[0] if blocks else response).strip()

def create_prompt(tokenizer, entry, vanilla, reference=None):
    if vanilla:
        instruction = VANILLA_INSTRUCTION.format(
            code=entry['declaration'] + entry['buggy_solution'])
    else:
        examples = ''.join(
            CRAFTED_INSTRUCTION.format(code=ex['code'], reference=ex['reference'], tests=ex['tests'])
            + f"\n\n### Response:\n{ex['answer']}\n<|EOT|>\n### Instruction:\n"
            for ex in EXAMPLES)
        instruction = examples + CRAFTED_INSTRUCTION.format(
            code=entry['prompt'] + entry['buggy_solution'],
            reference=reference,
            tests=entry['test'].strip())
    return wrap_prompt(tokenizer, instruction)

def extract_prediction(response):
    # Use the last tagged verdict; the model sometimes repeats the format example first.
    tagged = re.findall(r'<start>\s*\**\s*(buggy|correct)\b', response, re.IGNORECASE)
    if tagged:
        return tagged[-1].capitalize()
    return None

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
    print("Greedy decoding; max_new_tokens=512 for the reference step and 1024 for the verdict")

    results = []
    for entry in dataset:
        # TODO: create prompt for the model
        # Tip : Use can use any data from the dataset to create
        #       the prompt including prompt, canonical_solution, test, etc.
        reference_prompt = reference_response = None
        if not vanilla:
            # Step 1: let the model write its own implementation from the docstring alone, without
            # seeing the code under review, so that the reference is not biased by the bug.
            reference_prompt = wrap_prompt(tokenizer, REFERENCE_INSTRUCTION.format(prompt=entry['prompt']))
            reference_response = generate(model, tokenizer, reference_prompt, 512)
        prompt = create_prompt(tokenizer, entry, vanilla,
                               extract_code(reference_response) if reference_response else None)
        
        # TODO: prompt the model and get the response
        # Step 2 (crafted) or the only step (vanilla): ask for the bug verdict.
        response = generate(model, tokenizer, prompt, 1024)

        # TODO: process the response and save it to results
        # Every program in HumanEvalPack contains a bug, so the expected answer is "Buggy".
        prediction = extract_prediction(response)
        verdict = prediction == "Buggy"

        if reference_prompt is not None:
            print(f"Task_ID {entry['task_id']} reference step:\nprompt:\n{reference_prompt}\n"
                  f"response:\n{reference_response}")
        print(f"Task_ID {entry['task_id']}:\nprompt:\n{prompt}\nresponse:\n{response}\n"
              f"prediction:\n{prediction}\nis_expected:\n{verdict}")
        results.append({
            "task_id": entry["task_id"],
            "prompt": prompt,
            "response": response,
            "prediction": prediction,
            "reference_prompt": reference_prompt,
            "reference_response": reference_response,
            "is_correct": verdict
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
    This Python script is to run prompt LLMs for bug detection.
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
