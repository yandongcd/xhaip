## Summary
<!-- Brief description of the change -->

## Type
- [ ] Bug fix
- [ ] New feature
- [ ] Refactor
- [ ] Documentation
- [ ] CI/CD
- [ ] Other

## Checklist
- [ ] ruff check . = 0
- [ ] mypy packages/haip-core/haip/ = 0
- [ ] pytest packages/haip-core/tests/ tests/ -q (all green)
- [ ] python scripts/validate_agents.py (0 failures)
- [ ] python scripts/validate_patients.py (0 FAIL)
- [ ] New tests added for new functionality
- [ ] UI contracts pass: `pytest tests/test_ui_contracts.py`
- [ ] Handler contracts pass: `pytest tests/test_handler_contracts.py`

## Related
<!-- Link to issue or discussion -->
