import json, pathlib, importlib, re, sys

def load_jsonl(path):
    rows = []
    with open(path) as f:
        for line in f:
            rows.append(json.loads(line))
    return rows

def run_eval(rules_module, products_path, policy_path_core, policy_path_updates, eval_path):
    # In a real system, you'd load policies into the LLM prompt or RAG.
    # Here we just read them so we can pass them into the answer() signature.
    with open(policy_path_core) as f:
        policy_core = f.read()
    with open(policy_path_updates) as f:
        policy_updates = f.read()
    policies = policy_core + "\n" + policy_updates

    tests = load_jsonl(eval_path)
    passes = 0
    results = []
    for row in tests:
        out = rules_module.answer(row["q"], products_path, policies)
        ok = re.search(row["expect_regex"], out) is not None
        results.append({"id":row["id"], "q":row["q"], "out":out, "pass":ok})
        if ok: passes += 1
    score = round(100.0 * passes / max(1,len(tests)), 1)
    return score, results

if __name__ == "__main__":
    base = pathlib.Path("/mnt/data/agent_demo")
    sys.path.append(str(base))

    # 1) Baseline (before policy change) using rules_v1 and products.jsonl
    import rules_v1 as rules
    s1, r1 = run_eval(
        rules,
        str(base / "data" / "products.jsonl"),
        str(base / "policy_docs" / "policy_core.md"),
        str(base / "policy_docs" / "policy_updates.md"),
        str(base / "data" / "eval" / "qa_before.jsonl"),
    )
    print("[Baseline v1] score:", s1)

    # 2) After policy change: products_after + updated policy_updates_after.md
    # Still using rules_v1 (buggy) to show score drop
    s2, r2 = run_eval(
        rules,
        str(base / "data" / "products_after.jsonl"),
        str(base / "policy_docs" / "policy_core.md"),
        str(base / "policy_docs" / "policy_updates_after.md"),
        str(base / "data" / "eval" / "qa_after.jsonl"),
    )
    print("[After change v1 (BUG)] score:", s2)

    # 3) Apply "Morph" fix -> switch to rules_v2 (fixed)
    import rules_v2 as rules_fixed
    s3, r3 = run_eval(
        rules_fixed,
        str(base / "data" / "products_after.jsonl"),
        str(base / "policy_docs" / "policy_core.md"),
        str(base / "policy_docs" / "policy_updates_after.md"),
        str(base / "data" / "eval" / "qa_after.jsonl"),
    )
    print("[After change v2 (FIXED)] score:", s3)

    # Save a compact report for demo
    report = {
        "scores": {"baseline_v1": s1, "after_v1_bug": s2, "after_v2_fixed": s3},
        "sample_fails_v1": [row for row in r2 if not row["pass"]][:3],
        "sample_passes_v2": [row for row in r3 if row["pass"]][:3],
    }
    with open(base / "eval_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Report saved to:", str(base / "eval_report.json"))