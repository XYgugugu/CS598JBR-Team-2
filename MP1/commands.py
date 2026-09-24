###################################################################
# This is a list of all commands you need to run for MP1 on Colab.
###################################################################

# TODO: Update Your NetIDs in alphabetical order
NetIDs = ["dayuan", "encheng2", "yihangs"]
NetIDs_str = " ".join(NetIDs)

# TODO: Clone your GitHub repository
! git clone https://github.com/XYgugugu/CS598JBR-Team-2.git
%cd CS598JBR-Team-2

# Set up requirements for dataset generation
! bash -x MP1/setup_dataset.sh

# dataset generation
! python3 MP1/dataset_generation.py {NetIDs_str} |& tee dataset_generation.log

seed = "120462750136561247505675876249279604055"
# TODO: Replace the file path of selected_humaneval_[seed].jsonl generated in previous step
input_dataset = "selected_humaneval_" + seed + ".jsonl"

# Set up requirements for model prompting
! bash -x MP1/setup_models.sh

base_with_quantization = "base_prompt_" + seed + ".jsonl"
instruct_with_quantization = "instruct_prompt_" + seed + ".jsonl"
base_with_quantization_processed = "base_prompt_processed_" + seed + ".jsonl"
instruct_with_quantization_processed = "instruct_prompt_processed_" + seed + ".jsonl"

# Prompt the models
! python3 MP1/model_prompting.py {input_dataset} "deepseek-ai/deepseek-coder-6.7b-base" {base_with_quantization} {base_with_quantization_processed} "True" |& tee base_prompt.log
! python3 MP1/model_prompting.py {input_dataset} "deepseek-ai/deepseek-coder-6.7b-instruct" {instruct_with_quantization} {instruct_with_quantization_processed} "True" |& tee instruct_prompt.log

# evaluate the results to get pass@k
! evaluate_functional_correctness {base_with_quantization} |& tee base_evaluate.log
! evaluate_functional_correctness {instruct_with_quantization} |& tee instruct_evaluate.log
! evaluate_functional_correctness {base_with_quantization_processed} |& tee base_evaluate_processed.log
! evaluate_functional_correctness {instruct_with_quantization_processed} |& tee instruct_evaluate_processed.log

%cd ..

# git push all nessacery files (e.g., *jsonl, *log) to your GitHub repository
