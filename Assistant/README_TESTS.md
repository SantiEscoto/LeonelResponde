# Tests Strategy and Troubleshooting

This project has a few tests that exercise native libraries (PyTorch / Transformers / tokenizers and LLM backends). On certain environments (notably Python 3.9 with LibreSSL 2.8.3 on macOS), running all tests in a single process can lead to segmentation faults due to interactions between modules that load and unload native resources.

What we do to keep tests reliable and deterministic:

1) Global deterministic LLM teardown (automatic)
- The tests/conftest.py file defines a session-scoped, autouse fixture named global_llm_cleanup. This fixture ensures that any LLMManager instances left in memory are explicitly unloaded at the end of the test session and that CUDA cache is emptied when torch is available. This avoids unsafe destructor-time cleanup of native resources.
- You do not need to call unload() manually in individual tests, unless a test intentionally stresses teardown behavior.

2) Safe execution groups
- To avoid segfaults when combining certain modules, we run tests in two groups:
  - Group 1: Unit tests only
    - Command: pytest -q tests/unit
  - Group 2: Context-related tests, isolated in forked subprocesses
    - Command: pytest -q --forked test_context_improvements.py test_context_preservation.py test_robust_context_preservation.py test_user_session_switch.py
- The scripts/run_quality_checks.sh script already implements this grouping and enforces safe environment variables.

3) Environment knobs for stability
- We disable aggressive parallelism from native libs during test runs:
  - export TOKENIZERS_PARALLELISM=false
  - export OMP_NUM_THREADS=1
- These are set automatically by scripts/run_quality_checks.sh.

4) Running everything locally
- Recommended commands to run all tests safely:
  - Unit tests: pytest -q tests/unit
  - Context tests (forked): pytest -q --forked test_context_improvements.py test_context_preservation.py test_robust_context_preservation.py test_user_session_switch.py

5) Known fragile combinations
- On Python 3.9 + LibreSSL 2.8.3, the following combination can segfault when run in the same process:
  - tests/unit/test_unified_config.py together with test_context_improvements.py (and potentially other context_* tests).
- Running these in separate processes (using --forked) or in separate pytest invocations prevents the segmentation fault.

6) Mid/long-term recommendations
- Upgrade to Python 3.11+ and rebuild the virtual environment.
- Ensure your Python is linked against OpenSSL 1.1.1+ (not LibreSSL 2.8.3). This also removes urllib3 warnings.
- Pin combinations of PyTorch / Transformers / tokenizers that are verified stable for your OS and Python version.
- Consider mocking heavy LLM backends in unit tests to avoid exercise of native bindings when not required.


## CI Execution (Safe Two-Group Strategy)

To ensure CI runs are stable and avoid segmentation faults from native libraries interacting across unrelated tests, the workflow runs tests in two groups with conservative threading:

- Environment variables applied to all test steps:
  - TOKENIZERS_PARALLELISM=false
  - OMP_NUM_THREADS=1

- Group 1: Unit tests
  - Command: pytest -q tests/unit

- Group 2: Context-related tests in isolated subprocesses
  - Command: pytest -q --forked \
    test_context_improvements.py \
    test_context_preservation.py \
    test_robust_context_preservation.py \
    test_user_session_switch.py

Rationale:
- Forking creates a fresh process for the context tests, preventing cross-test contamination of native state (PyTorch/Transformers/tokenizers) that previously caused segmentation faults when sharing a single process.

Notes:
- The session-scoped autouse fixture global_llm_cleanup in tests/conftest.py remains fully compatible and provides deterministic resource teardown at session end.
- See .github/workflows/ci-tests.yml for a reference GitHub Actions configuration implementing this strategy.


## Merge Protection and Required Status Checks (GitHub Actions)

This repository enforces safe merges into the main branch by requiring the GitHub Actions workflow CI - Safe Tests to pass before merges are allowed. The workflow already runs tests in two groups inside a single job (tests):

- Step: Run unit tests (Group 1)
  - Command: pytest -q tests/unit
  - Environment: TOKENIZERS_PARALLELISM=false, OMP_NUM_THREADS=1

- Step: Run context tests with process isolation (Group 2)
  - Command: pytest -q --forked \
    test_context_improvements.py \
    test_context_preservation.py \
    test_robust_context_preservation.py \
    test_user_session_switch.py
  - Environment: TOKENIZERS_PARALLELISM=false, OMP_NUM_THREADS=1

Important:
- GitHub branch protection can require checks at the job level (not per-step). Making the job CI - Safe Tests / tests required effectively ensures BOTH steps must pass, because a failure in any step fails the job.
- This requirement applies only to pull requests targeting main (by configuring a branch protection rule for main). It does not block pushes to other branches.

How to enable required status checks (Repository Admins):
1) In GitHub, go to: Settings → Branches → Branch protection rules → Add rule
2) Set Branch name pattern to main
3) Enable Require a pull request before merging
4) Enable Require status checks to pass before merging
5) In the search field, select the specific check: CI - Safe Tests / tests
6) (Optional) Keep other protections as needed (e.g., dismiss stale approvals, required reviews)
7) Save changes

Rationale and compatibility:
- The two-group strategy eliminates segfaults by isolating context tests with --forked, while unit tests run normally but with conservative threading.
- The session-scoped autouse fixture global_llm_cleanup remains fully compatible, ensuring deterministic unload of LLM resources and CUDA cache cleanup.

Developer verification steps:
1) Open a PR against main to trigger the workflow CI - Safe Tests
2) In the PR, open the Checks tab and confirm there is a required check named CI - Safe Tests / tests
3) Confirm that both internal steps ran:
   - Run unit tests (Group 1)
   - Run context tests with process isolation (Group 2)
4) Ensure the check is required (the Merge button should be disabled until it passes). If you see “Required” next to the check, the branch protection is active.
5) (Optional) To test failure behavior, temporarily break a unit or context test in a feature branch, push, and verify the check turns red and the merge is blocked. Revert the change and push again to see the check turn green and the merge become allowed.

Notes:
- No changes to the existing workflow file are necessary to enforce merge protection; the branch protection rule on main is sufficient. The job-level required check ensures both groups pass.
- If you ever want per-group required checks (separate check names), you would need to split these steps into separate jobs or workflows. That change is not required for the current setup.