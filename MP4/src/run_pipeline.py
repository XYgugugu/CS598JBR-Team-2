import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime

MP4_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LOG_FILE = None


def log(message):
    line = "[" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "] " + message
    print(line, flush=True)
    if LOG_FILE is not None:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")


def read_text(path):
    with open(path, "r") as f:
        return f.read()


def write_text(path, text):
    with open(path, "w") as f:
        f.write(text)


def mp4_path(relative_path):
    return os.path.join(MP4_DIR, relative_path)


def redact_secrets(text):
    return re.sub(r"sk-ant-[A-Za-z0-9_\-]+", "[REDACTED]", text)


def shorten(text, max_chars):
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return text[:half] + "\n\n... [output shortened] ...\n\n" + text[-half:]


def make_environment():
    env = os.environ.copy()
    cargo_bin = os.path.join(os.path.expanduser("~"), ".cargo", "bin")
    env["PATH"] = cargo_bin + os.pathsep + env.get("PATH", "")
    return env


def run_command(command, cwd, timeout, input_text=None):
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            env=make_environment(),
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT: command did not finish within " + str(timeout) + " seconds"


def list_files(folder, extensions, skip_folder=None):
    found = []
    for root, dirs, files in os.walk(folder):
        dirs.sort()
        if skip_folder is not None and os.path.abspath(root).startswith(os.path.abspath(skip_folder)):
            continue
        for name in sorted(files):
            if name.endswith(tuple(extensions)):
                found.append(os.path.relpath(os.path.join(root, name), folder))
    return found


def as_bullet_list(items):
    if not items:
        return "- (none)"
    return "\n".join("- `" + item + "`" for item in items)


def save_protected_files(translation_dir, protected_paths):
    saved = {}
    for path in protected_paths:
        full_path = os.path.join(translation_dir, path)
        if os.path.isdir(full_path):
            for name in list_files(full_path, [""]):
                relative = os.path.join(path, name)
                with open(os.path.join(translation_dir, relative), "rb") as f:
                    saved[relative] = f.read()
        elif os.path.isfile(full_path):
            with open(full_path, "rb") as f:
                saved[path] = f.read()
    return saved


def check_and_restore_protected_files(translation_dir, saved_files):
    problems = []
    for relative, original_content in saved_files.items():
        full_path = os.path.join(translation_dir, relative)
        current_content = None
        if os.path.isfile(full_path):
            with open(full_path, "rb") as f:
                current_content = f.read()
        if current_content != original_content:
            problems.append(relative + " was modified or deleted (restored to the original)")
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as f:
                f.write(original_content)
    return problems


def run_agent(config, prompt, translation_dir, subject_dir, session_id, round_number, trajectory_dir):
    agent = config["agent"]
    system_prompt = read_text(mp4_path(agent["system_prompt_file"]))

    command = [
        agent["command"], "-p",
        "--model", agent["model"],
        "--effort", agent["effort"],
        "--output-format", "stream-json",
        "--verbose",
        "--append-system-prompt", system_prompt,
        "--settings", mp4_path(agent["settings_file"]),
        "--permission-mode", agent["permission_mode"],
        "--tools", agent["tools"],
        "--setting-sources", "project",
        "--strict-mcp-config",
        "--max-budget-usd", str(agent["max_budget_usd_per_round"]),
        "--add-dir", subject_dir,
    ]
    if session_id is not None:
        command += ["--resume", session_id]

    raw_log_path = os.path.join(trajectory_dir, "round_" + str(round_number) + "_agent.jsonl")
    stderr_path = os.path.join(trajectory_dir, "round_" + str(round_number) + "_agent_stderr.txt")

    log("Starting agent (round " + str(round_number) + ")"
        + (" resuming session " + session_id if session_id else " with a new session"))

    result_event = None
    with open(raw_log_path, "w") as raw_log, open(stderr_path, "w") as stderr_file:
        process = subprocess.Popen(
            command,
            cwd=translation_dir,
            env=make_environment(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr_file,
            text=True,
        )
        process.stdin.write(prompt)
        process.stdin.close()

        for line in process.stdout:
            raw_log.write(redact_secrets(line))
            raw_log.flush()
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "assistant":
                for block in event["message"].get("content", []):
                    if block.get("type") == "tool_use":
                        log("  agent tool call: " + describe_tool_call(block))
            if event.get("type") == "result":
                result_event = event
        process.wait()

    write_readable_transcript(raw_log_path, raw_log_path.replace("_agent.jsonl", "_transcript.md"))

    info = {
        "exit_code": process.returncode,
        "session_id": session_id,
        "cost_usd": 0.0,
        "num_turns": 0,
        "is_error": True,
        "final_message": "",
    }
    if result_event is not None:
        info["session_id"] = result_event.get("session_id", session_id)
        info["cost_usd"] = result_event.get("total_cost_usd", 0.0)
        info["num_turns"] = result_event.get("num_turns", 0)
        info["is_error"] = result_event.get("is_error", True)
        info["final_message"] = result_event.get("result", "")
    log("Agent finished: exit code " + str(info["exit_code"]) + ", turns " + str(info["num_turns"])
        + ", cost $" + str(round(info["cost_usd"], 2)))
    return info


def describe_tool_call(block):
    tool_input = block.get("input", {})
    if "command" in tool_input:
        detail = tool_input["command"]
    elif "file_path" in tool_input:
        detail = tool_input["file_path"]
    elif "pattern" in tool_input:
        detail = tool_input["pattern"]
    else:
        detail = json.dumps(tool_input)
    return block.get("name", "?") + ": " + shorten(detail.replace("\n", " "), 200)


def write_readable_transcript(raw_log_path, transcript_path):
    lines = ["# Agent transcript", ""]
    with open(raw_log_path, "r") as f:
        for line in f:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            if event.get("type") == "assistant":
                for block in event["message"].get("content", []):
                    if block.get("type") == "text":
                        lines += ["## Agent", "", block["text"], ""]
                    elif block.get("type") == "tool_use":
                        lines += ["### Tool call: " + describe_tool_call(block), ""]
                        if block.get("name") in ("Edit", "Write"):
                            new_code = block["input"].get("new_string") or block["input"].get("content") or ""
                            lines += ["```rust", shorten(new_code, 4000), "```", ""]

            elif event.get("type") == "user":
                content = event.get("message", {}).get("content", [])
                if isinstance(content, str):
                    continue
                for block in content:
                    if block.get("type") != "tool_result":
                        continue
                    output = block.get("content", "")
                    if isinstance(output, list):
                        output = "\n".join(part.get("text", "") for part in output if isinstance(part, dict))
                    title = "### Tool result (error)" if block.get("is_error") else "### Tool result"
                    lines += [title, "", "```", shorten(str(output), 3000), "```", ""]

            elif event.get("type") == "result":
                lines += ["## Final result", "",
                          "- turns: " + str(event.get("num_turns")),
                          "- cost (USD): " + str(event.get("total_cost_usd")),
                          "- error: " + str(event.get("is_error")),
                          "", str(event.get("result", "")), ""]

    write_text(transcript_path, redact_secrets("\n".join(lines)))


def check_build(config, translation_dir):
    toolchain = "+" + config["toolchain"]
    timeout = config["checks"]["timeout_seconds"]
    exit_code, output = run_command(["cargo", toolchain, "build"], translation_dir, timeout)
    return exit_code == 0, output


def check_tests(config, translation_dir):
    toolchain = "+" + config["toolchain"]
    timeout = config["checks"]["timeout_seconds"]
    exit_code, output = run_command(["cargo", toolchain, "test", "--no-fail-fast"], translation_dir, timeout)

    test_status = {}
    current_source = "?"
    for line in output.splitlines():
        running = re.match(r"\s*Running (?:unittests )?(\S+)", line)
        if running:
            current_source = running.group(1)
            continue
        result = re.match(r"test (\S+) \.\.\. (ok|FAILED|ignored)", line)
        if result:
            key = (current_source, result.group(1))
            if test_status.get(key) != "FAILED":
                test_status[key] = result.group(2)

    passed = sum(1 for status in test_status.values() if status == "ok")
    failed_names = sorted(source + "::" + name for (source, name), status in test_status.items() if status == "FAILED")
    return {
        "passed": passed,
        "total": len(test_status),
        "failed_tests": failed_names,
        "output": output,
    }


def check_clippy(config, translation_dir):
    toolchain = "+" + config["toolchain"]
    timeout = config["checks"]["timeout_seconds"]
    categories = config["checks"]["clippy_categories"]

    official_command = ["cargo", toolchain, "clippy", "--all-targets", "--all-features", "--"]
    for category in categories:
        official_command += ["-W", "clippy::" + category]
    exit_code, official_output = run_command(official_command, translation_dir, timeout)

    counts = {}
    counts_with_tests = {}
    for category in categories:
        command = ["cargo", toolchain, "clippy", "--all-targets", "--all-features",
                   "--message-format=json", "--", "-A", "clippy::all", "-W", "clippy::" + category]
        exit_code, output = run_command(command, translation_dir, timeout)
        all_warnings = set()
        own_code_warnings = set()
        for line in output.splitlines():
            if not line.startswith("{"):
                continue
            message = json.loads(line)
            if message.get("reason") != "compiler-message":
                continue
            diagnostic = message["message"]
            code = (diagnostic.get("code") or {}).get("code") or ""
            if not code.startswith("clippy::") or diagnostic.get("level") != "warning":
                continue
            all_warnings.add(diagnostic["rendered"])
            file_name = diagnostic["spans"][0]["file_name"] if diagnostic["spans"] else ""
            if not file_name.startswith("src/bin/"):
                own_code_warnings.add(diagnostic["rendered"])
        counts[category] = len(own_code_warnings)
        counts_with_tests[category] = len(all_warnings)

    return {
        "counts": counts,
        "total": sum(counts.values()),
        "counts_with_tests": counts_with_tests,
        "total_with_tests": sum(counts_with_tests.values()),
        "output": official_output,
    }


def check_unsafe_metrics(config, translation_dir, metrics_json_path):
    toolchain = "+" + config["toolchain"]
    timeout = config["checks"]["timeout_seconds"]

    run_command(["cargo", toolchain, "clean"], translation_dir, timeout)
    exit_code, raw_output = run_command(["cargo", toolchain, "newmetrics"], translation_dir, timeout)

    aggregate_script = mp4_path(config["checks"]["newmetrics_aggregate_script"])
    run_command(["python3", aggregate_script, "--out", metrics_json_path], translation_dir, timeout, input_text=raw_output)

    if not os.path.isfile(metrics_json_path):
        return None, raw_output
    with open(metrics_json_path) as f:
        return json.load(f), raw_output


def run_all_checks(config, translation_dir, round_number, trajectory_dir):
    log("Running checks for round " + str(round_number))
    prefix = os.path.join(trajectory_dir, "round_" + str(round_number))

    build_ok, build_output = check_build(config, translation_dir)
    log("  build: " + ("OK" if build_ok else "FAILED"))

    tests = {"passed": 0, "total": 0, "failed_tests": [], "output": "(skipped: build failed)"}
    clippy = {"counts": {}, "total": None, "counts_with_tests": {}, "total_with_tests": None,
              "output": "(skipped: build failed)"}
    metrics, metrics_output = None, "(skipped: build failed)"

    if build_ok:
        tests = check_tests(config, translation_dir)
        log("  tests: " + str(tests["passed"]) + "/" + str(tests["total"]) + " passed")
        clippy = check_clippy(config, translation_dir)
        log("  clippy (own code): " + json.dumps(clippy["counts"])
            + ", including test files: " + json.dumps(clippy["counts_with_tests"]))
        metrics, metrics_output = check_unsafe_metrics(config, translation_dir, prefix + "_unsafe_metrics.json")
        log("  unsafe metrics: " + json.dumps(metrics))

    report = [
        "=== BUILD (exit ok: " + str(build_ok) + ") ===", build_output,
        "=== TESTS ===", tests["output"],
        "=== CLIPPY ===", clippy["output"],
        "=== UNSAFE METRICS (newmetrics raw output) ===", metrics_output,
    ]
    write_text(prefix + "_checks.txt", redact_secrets("\n".join(report)))

    return {
        "round": round_number,
        "build_ok": build_ok,
        "build_output": build_output,
        "tests_passed": tests["passed"],
        "tests_total": tests["total"],
        "failed_tests": tests["failed_tests"],
        "test_output": tests["output"],
        "clippy_counts": clippy["counts"],
        "clippy_total": clippy["total"],
        "clippy_counts_with_tests": clippy["counts_with_tests"],
        "clippy_total_with_tests": clippy["total_with_tests"],
        "clippy_output": clippy["output"],
        "unsafe_metrics": metrics,
    }


def unsafe_total(metrics):
    if metrics is None:
        return None
    keys = ["unsafe_lines", "unsafe_calls", "unsafe_casts", "pointer_arithmetic"]
    return sum(metrics.get(key, 0) for key in keys)


def all_checks_pass(checks, config, protected_problems):
    max_clippy = config["stopping_condition"]["max_clippy_warnings_in_own_code"]
    return (
        checks["build_ok"]
        and checks["tests_total"] > 0
        and checks["tests_passed"] == checks["tests_total"]
        and checks["clippy_total"] is not None
        and checks["clippy_total"] <= max_clippy
        and unsafe_total(checks["unsafe_metrics"]) == 0
        and len(protected_problems) == 0
    )


def progress_key(checks):
    return (checks["build_ok"], checks["tests_passed"], checks["clippy_total"], unsafe_total(checks["unsafe_metrics"]))


def build_initial_prompt(config, project, subject_dir, translation_dir):
    template = read_text(mp4_path(config["agent"]["initial_prompt_file"]))
    c_files = list_files(subject_dir, [".c", ".h"])
    interface_files = list_files(os.path.join(translation_dir, "src"), [".rs"],
                                 skip_folder=os.path.join(translation_dir, "src", "bin"))
    test_files = list_files(os.path.join(translation_dir, "src", "bin"), [".rs"])

    prompt = template
    prompt = prompt.replace("{project_name}", project["name"])
    prompt = prompt.replace("{subject_dir}", subject_dir)
    prompt = prompt.replace("{translation_dir}", translation_dir)
    prompt = prompt.replace("{c_files}", as_bullet_list(c_files))
    prompt = prompt.replace("{interface_files}", as_bullet_list(["src/" + f for f in interface_files]))
    prompt = prompt.replace("{test_files}", as_bullet_list(["src/bin/" + f for f in test_files]))
    return prompt


def build_repair_prompt(config, checks, protected_problems, round_number):
    template = read_text(mp4_path(config["agent"]["repair_prompt_file"]))
    max_chars = config["checks"]["max_feedback_chars_per_section"]

    sections = []
    if protected_problems:
        sections.append("### Protected files\n\nThe following files must not be changed. "
                        "They were restored:\n\n" + as_bullet_list(protected_problems))
    if not checks["build_ok"]:
        sections.append("### Build errors\n\n```\n" + shorten(checks["build_output"], max_chars) + "\n```")
    if checks["build_ok"] and checks["tests_passed"] < checks["tests_total"]:
        interesting = [line for line in checks["test_output"].splitlines()
                       if not line.rstrip().endswith("... ok") and not line.strip().startswith("Compiling")]
        sections.append("### Failing tests\n\n" + as_bullet_list(checks["failed_tests"])
                        + "\n\n```\n" + shorten("\n".join(interesting), max_chars) + "\n```")
    if checks["clippy_total"]:
        sections.append("### Clippy output\n\n```\n" + shorten(checks["clippy_output"], max_chars) + "\n```")
    if unsafe_total(checks["unsafe_metrics"]):
        sections.append("### Unsafe metrics\n\nThe unsafe-code analyzer still finds unsafe code. "
                        "Remove it and use safe Rust instead.\n\n```\n"
                        + json.dumps(checks["unsafe_metrics"], indent=2) + "\n```")
    if checks["build_ok"] and checks["unsafe_metrics"] is None:
        sections.append("### Unsafe metrics\n\nThe unsafe-code analyzer could not run on this project.")

    prompt = template
    prompt = prompt.replace("{round}", str(round_number))
    prompt = prompt.replace("{max_rounds}", str(config["stopping_condition"]["max_rounds"]))
    prompt = prompt.replace("{build_status}", "OK" if checks["build_ok"] else "FAILED")
    prompt = prompt.replace("{tests_passed}", str(checks["tests_passed"]))
    prompt = prompt.replace("{tests_total}", str(checks["tests_total"]))
    prompt = prompt.replace("{clippy_summary}", json.dumps(checks["clippy_counts"]))
    prompt = prompt.replace("{unsafe_summary}", json.dumps(checks["unsafe_metrics"]))
    prompt = prompt.replace("{protected_status}", "restored after changes" if protected_problems else "unchanged")
    prompt = prompt.replace("{feedback}", "\n\n".join(sections) if sections else "(no details)")
    return prompt


def summary_row(checks, agent_info, protected_problems):
    return {
        "round": checks["round"],
        "build_ok": checks["build_ok"],
        "tests_passed": checks["tests_passed"],
        "tests_total": checks["tests_total"],
        "failed_tests": checks["failed_tests"],
        "clippy_counts": checks["clippy_counts"],
        "clippy_total": checks["clippy_total"],
        "clippy_counts_with_tests": checks["clippy_counts_with_tests"],
        "clippy_total_with_tests": checks["clippy_total_with_tests"],
        "unsafe_metrics": checks["unsafe_metrics"],
        "protected_file_problems": protected_problems,
        "agent": agent_info,
    }


def main():
    global LOG_FILE

    if len(sys.argv) != 2:
        print("Usage: python3 src/run_pipeline.py <project number, e.g. 1 or 2>")
        sys.exit(1)
    project_number = sys.argv[1]

    config = json.loads(read_text(mp4_path("configs/pipeline.json")))
    if project_number not in config["projects"]:
        print("Unknown project: " + project_number)
        sys.exit(1)
    project = config["projects"][project_number]

    subject_dir = mp4_path(project["subject_dir"])
    translation_dir = mp4_path(project["translation_dir"])
    trajectory_dir = mp4_path(project["trajectory_dir"])
    max_rounds = config["stopping_condition"]["max_rounds"]

    if os.path.isdir(trajectory_dir):
        shutil.rmtree(trajectory_dir)
    os.makedirs(trajectory_dir)
    LOG_FILE = os.path.join(trajectory_dir, "execution.log")

    log("Project " + project_number + ": " + project["name"])
    log("Model: " + config["agent"]["model"] + ", effort: " + config["agent"]["effort"]
        + ", max rounds: " + str(max_rounds))

    protected_files = save_protected_files(translation_dir, config["protected_files"])
    log("Protected files: " + ", ".join(sorted(protected_files.keys())))

    baseline = run_all_checks(config, translation_dir, 0, trajectory_dir)
    rounds = [summary_row(baseline, None, [])]

    prompt = build_initial_prompt(config, project, subject_dir, translation_dir)
    session_id = None
    previous_checks = None
    stop_reason = "max_rounds_reached"
    total_cost = 0.0

    for round_number in range(1, max_rounds + 1):
        write_text(os.path.join(trajectory_dir, "round_" + str(round_number) + "_prompt.md"), prompt)

        agent_info = run_agent(config, prompt, translation_dir, subject_dir, session_id,
                               round_number, trajectory_dir)
        session_id = agent_info["session_id"]
        total_cost += agent_info["cost_usd"] or 0.0

        protected_problems = check_and_restore_protected_files(translation_dir, protected_files)
        for problem in protected_problems:
            log("  WARNING: " + problem)
        checks = run_all_checks(config, translation_dir, round_number, trajectory_dir)
        rounds.append(summary_row(checks, agent_info, protected_problems))

        if all_checks_pass(checks, config, protected_problems):
            stop_reason = "all_checks_passed"
            break
        if session_id is None:
            stop_reason = "agent_failed_to_start"
            break
        if (config["stopping_condition"]["stop_when_no_progress"]
                and previous_checks is not None
                and progress_key(checks) == progress_key(previous_checks)
                and not protected_problems):
            stop_reason = "no_progress"
            break
        if round_number == max_rounds:
            break

        prompt = build_repair_prompt(config, checks, protected_problems, round_number)
        previous_checks = checks

    final = rounds[-1]
    log("Stopped: " + stop_reason)
    log("Final: build " + ("OK" if final["build_ok"] else "FAILED")
        + ", tests " + str(final["tests_passed"]) + "/" + str(final["tests_total"])
        + ", clippy (own code) " + json.dumps(final["clippy_counts"])
        + ", clippy (with tests) " + json.dumps(final["clippy_counts_with_tests"])
        + ", unsafe " + json.dumps(final["unsafe_metrics"]))
    log("Agent rounds: " + str(len(rounds) - 1) + ", total cost: $" + str(round(total_cost, 2)))

    summary = {
        "project_number": project_number,
        "project_name": project["name"],
        "model": config["agent"]["model"],
        "effort": config["agent"]["effort"],
        "toolchain": config["toolchain"],
        "stop_reason": stop_reason,
        "agent_rounds": len(rounds) - 1,
        "total_cost_usd": total_cost,
        "rounds": rounds,
    }
    write_text(os.path.join(trajectory_dir, "summary.json"), json.dumps(summary, indent=2))

    run_command(["cargo", "+" + config["toolchain"], "clean"], translation_dir, config["checks"]["timeout_seconds"])


if __name__ == "__main__":
    main()
